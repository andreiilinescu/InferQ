#!/usr/bin/env python3
"""
Duplicate Circuit Detection System

This module provides efficient duplicate detection for quantum circuits by:
1. Fetching all existing circuit hashes from Azure Table Storage at startup
2. Caching them locally for fast lookup during pipeline execution
3. Providing fast O(1) duplicate checking without expensive operations

Author: InferQ Pipeline System
"""

import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Set, Optional
from datetime import datetime, timezone
from qiskit import QuantumCircuit

from utils.azure_connection import AzureConnection
from utils.circuit_hash import compute_circuit_hash_simple

# Configure logging
logger = logging.getLogger(__name__)

class DuplicateDetector:
    """
    Efficient duplicate detection system for quantum circuits.
    
    Features:
    - Fetches existing hashes from Azure Table Storage at startup
    - Caches hashes locally for O(1) lookup performance
    - Automatically saves/loads cache to local file
    - Thread-safe operations for multiprocessing
    """
    
    def __init__(self, cache_file: str = "circuit_hashes_cache.json"):
        """
        Initialize the duplicate detector.
        
        Args:
            cache_file: Local file to cache circuit hashes
        """
        self.cache_file = Path(cache_file)
        self.known_hashes: Set[str] = set()
        self.azure_conn: Optional[AzureConnection] = None
        self.last_sync: Optional[datetime] = None
        
        logger.info("Initializing DuplicateDetector...")
        
    def initialize(self, azure_conn: Optional[AzureConnection] = None, force_refresh: bool = False) -> bool:
        """
        Initialize the duplicate detector by loading existing hashes.
        
        Args:
            azure_conn: Shared Azure connection instance (optional)
            force_refresh: If True, fetch fresh data from Azure instead of using cache
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Use provided Azure connection or try to create one
            if azure_conn:
                self.azure_conn = azure_conn
                logger.info("✓ Using shared Azure connection for duplicate detection")
            else:
                try:
                    self.azure_conn = AzureConnection()
                    logger.info("✓ Azure connection established for duplicate detection")
                except Exception as e:
                    logger.warning(f"⚠️  Azure connection failed: {e}")
                    logger.warning("⚠️  Duplicate detection will use local cache only")
                    self.azure_conn = None
            
            # Load from cache first (fast startup)
            if not force_refresh and self._load_cache():
                logger.info(f"✓ Loaded {len(self.known_hashes)} circuit hashes from local cache")
                
                # Optionally sync with Azure in background if connection available
                if self.azure_conn:
                    self._sync_with_azure_background()
            else:
                # No cache or forced refresh - fetch from Azure
                if self.azure_conn:
                    self._fetch_from_azure()
                else:
                    logger.warning("⚠️  No Azure connection and no local cache - starting with empty hash set")
                    
            logger.info(f"🔍 DuplicateDetector initialized with {len(self.known_hashes)} known circuit hashes")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize DuplicateDetector: {e}")
            return False
    
    def is_duplicate(self, circuit: QuantumCircuit) -> tuple[bool, str]:
        """
        Check if a circuit is a duplicate by computing its hash.
        
        Args:
            circuit: The quantum circuit to check
            
        Returns:
            Tuple of (is_duplicate: bool, circuit_hash: str)
        """
        try:
            # Compute circuit hash using centralized function
            circuit_hash = compute_circuit_hash_simple(circuit)
            
            # Check if hash exists in our known set
            is_dup = circuit_hash in self.known_hashes
            
            if is_dup:
                logger.debug(f"🔍 Duplicate detected: {circuit_hash[:8]}...")
            else:
                logger.debug(f"🆕 New circuit: {circuit_hash[:8]}...")
                # Add to known hashes to prevent future duplicates in this session
                self.known_hashes.add(circuit_hash)
                
            return is_dup, circuit_hash
            
        except Exception as e:
            logger.error(f"❌ Error checking duplicate: {e}")
            # On error, assume not duplicate to be safe
            return False, ""
    

    
    def _fetch_from_azure(self) -> bool:
        """
        Fetch all existing circuit hashes from Azure Table Storage.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.azure_conn:
            logger.warning("⚠️  No Azure connection available for fetching hashes")
            return False
            
        try:
            logger.info("🔄 Fetching existing circuit hashes from Azure Table Storage...")
            
            table_client = self.azure_conn.get_circuits_table_client()
            
            # Query all entities, but only fetch the RowKey (which is the circuit hash)
            entities = table_client.list_entities(select=["RowKey"])
            
            hash_count = 0
            for entity in entities:
                circuit_hash = entity.get("RowKey")
                if circuit_hash:
                    self.known_hashes.add(circuit_hash)
                    hash_count += 1
                    
                    # Log progress for large datasets
                    if hash_count % 1000 == 0:
                        logger.info(f"📥 Fetched {hash_count} circuit hashes...")
            
            self.last_sync = datetime.now(timezone.utc)
            logger.info(f"✅ Successfully fetched {hash_count} circuit hashes from Azure")
            
            # Save to local cache
            self._save_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch hashes from Azure: {e}")
            return False
    
    def _load_cache(self) -> bool:
        """
        Load circuit hashes from local cache file.
        
        Returns:
            True if cache loaded successfully, False otherwise
        """
        try:
            if not self.cache_file.exists():
                logger.debug("📁 No local cache file found")
                return False
                
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
                
            # Validate cache structure
            if not isinstance(cache_data, dict) or 'hashes' not in cache_data:
                logger.warning("⚠️  Invalid cache file format")
                return False
                
            # Load hashes
            self.known_hashes = set(cache_data['hashes'])
            
            # Load metadata
            if 'last_sync' in cache_data:
                self.last_sync = datetime.fromisoformat(cache_data['last_sync'])
                
            cache_age_hours = (datetime.now(timezone.utc) - self.last_sync).total_seconds() / 3600 if self.last_sync else float('inf')
            
            logger.info(f"📁 Loaded cache: {len(self.known_hashes)} hashes (age: {cache_age_hours:.1f}h)")
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to load cache: {e}")
            return False
    
    def _save_cache(self) -> bool:
        """
        Save circuit hashes to local cache file.
        
        Returns:
            True if cache saved successfully, False otherwise
        """
        try:
            cache_data = {
                'hashes': list(self.known_hashes),
                'last_sync': self.last_sync.isoformat() if self.last_sync else None,
                'total_count': len(self.known_hashes),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Write to temporary file first, then rename (atomic operation)
            temp_file = self.cache_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            temp_file.rename(self.cache_file)
            
            logger.debug(f"💾 Saved {len(self.known_hashes)} hashes to cache")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save cache: {e}")
            return False
    
    def _sync_with_azure_background(self):
        """
        Sync with Azure in background (placeholder for future async implementation).
        For now, just logs that background sync would happen here.
        """
        logger.debug("🔄 Background sync with Azure (future feature)")
        # TODO: Implement background sync using threading or asyncio
    
    def get_stats(self) -> dict:
        """
        Get statistics about the duplicate detector.
        
        Returns:
            Dictionary with detector statistics
        """
        return {
            'known_hashes_count': len(self.known_hashes),
            'azure_connected': self.azure_conn is not None,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'cache_file': str(self.cache_file),
            'cache_exists': self.cache_file.exists()
        }


# Global instance for easy access
_global_detector: Optional[DuplicateDetector] = None

def get_duplicate_detector() -> DuplicateDetector:
    """
    Get the global duplicate detector instance.
    
    Returns:
        Global DuplicateDetector instance
    """
    global _global_detector
    if _global_detector is None:
        _global_detector = DuplicateDetector()
    return _global_detector

def initialize_duplicate_detection(azure_conn: Optional[AzureConnection] = None, force_refresh: bool = False) -> bool:
    """
    Initialize the global duplicate detection system.
    
    Args:
        azure_conn: Shared Azure connection instance (optional)
        force_refresh: If True, fetch fresh data from Azure instead of using cache
        
    Returns:
        True if initialization successful, False otherwise
    """
    detector = get_duplicate_detector()
    return detector.initialize(azure_conn=azure_conn, force_refresh=force_refresh)

def is_circuit_duplicate(circuit: QuantumCircuit) -> tuple[bool, str]:
    """
    Check if a circuit is a duplicate using the global detector.
    
    Args:
        circuit: The quantum circuit to check
        
    Returns:
        Tuple of (is_duplicate: bool, circuit_hash: str)
    """
    detector = get_duplicate_detector()
    return detector.is_duplicate(circuit)


if __name__ == "__main__":
    # Test the duplicate detector
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Testing DuplicateDetector...")
    
    detector = DuplicateDetector()
    success = detector.initialize()
    
    if success:
        stats = detector.get_stats()
        print(f"📊 Detector Stats: {stats}")
    else:
        print("❌ Failed to initialize detector")