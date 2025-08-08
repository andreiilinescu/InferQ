#!/usr/bin/env python3
"""
Azure Upload Manager Module

Handles batch uploads of circuits to Azure storage with detailed logging
and error handling. Provides efficient batch processing and comprehensive
status reporting.

Author: InferQ Pipeline System
"""

import logging
from typing import List, Dict, Any

from utils.azure_connection import AzureConnection
from utils.save_utils import upload_circuit_blob, save_circuit_metadata_to_table

# Configure logging
logger = logging.getLogger(__name__)

def upload_batch_to_azure(circuit_batch: List[Dict[str, Any]], azure_conn: AzureConnection) -> Dict[str, Any]:
    """
    Upload a batch of circuits to Azure storage in parallel.
    
    Args:
        circuit_batch: List of circuit results to upload
        azure_conn: Azure connection instance
        
    Returns:
        Dictionary with upload statistics
    """
    if not azure_conn:
        return {'uploaded': 0, 'failed': 0, 'error': 'No Azure connection'}
    
    uploaded = 0
    failed = 0
    
    # Log the start of Azure upload batch
    logger.warning(f"🔄 AZURE UPLOAD STARTING: Processing {len(circuit_batch)} circuits for cloud storage")
    
    try:
        container_client = azure_conn.get_container_client()
        table_client = azure_conn.get_circuits_table_client()
        
        for i, result in enumerate(circuit_batch, 1):
            if not result.get('success') or not result.get('written'):
                continue
                
            try:
                circuit = result['circuit']
                features = result['features']
                qpy_hash = result['circuit_hash']
                serialization_method = result['serialization_method']
                worker_id = result.get('worker_id', 'unknown')
                
                logger.warning(f"☁️  UPLOADING [{i}/{len(circuit_batch)}]: Circuit {qpy_hash[:8]}... from Worker-{worker_id} ({circuit.num_qubits}q, depth={circuit.depth()})")
                
                # Upload to blob storage
                blob_path = upload_circuit_blob(
                    container_client, circuit, qpy_hash, serialization_method
                )
                features["blob_path"] = blob_path.split("circuits/")[1] if "circuits/" in blob_path else blob_path
                
                # Save metadata to table storage
                table_success = save_circuit_metadata_to_table(table_client, features)
                
                if table_success:
                    uploaded += 1
                    logger.warning(f"✅ AZURE SUCCESS [{i}/{len(circuit_batch)}]: Circuit {qpy_hash[:8]}... uploaded to cloud storage")
                else:
                    failed += 1
                    logger.warning(f"❌ AZURE METADATA FAILED [{i}/{len(circuit_batch)}]: Circuit {qpy_hash[:8]}... blob uploaded but metadata failed")
                    
            except Exception as e:
                failed += 1
                circuit_hash = result.get('circuit_hash', 'unknown')[:8] + '...' if result.get('circuit_hash') else 'unknown'
                logger.warning(f"❌ AZURE UPLOAD FAILED [{i}/{len(circuit_batch)}]: Circuit {circuit_hash} - {str(e)}")
                
    except Exception as e:
        logger.warning(f"❌ AZURE BATCH FAILED: Critical error during batch upload - {str(e)}")
        return {'uploaded': 0, 'failed': len(circuit_batch), 'error': str(e)}
    
    # Log the completion of Azure upload batch
    if uploaded > 0:
        logger.warning(f"🎉 AZURE UPLOAD COMPLETED: {uploaded} circuits successfully stored in cloud, {failed} failed")
    else:
        logger.warning(f"⚠️  AZURE UPLOAD COMPLETED: No circuits uploaded, {failed} failed")
    
    return {'uploaded': uploaded, 'failed': failed}

def should_trigger_upload(upload_buffer: List[Dict[str, Any]], azure_upload_interval: int) -> bool:
    """
    Check if Azure upload should be triggered based on buffer size.
    
    Args:
        upload_buffer: Current upload buffer
        azure_upload_interval: Upload threshold
        
    Returns:
        True if upload should be triggered, False otherwise
    """
    return len(upload_buffer) >= azure_upload_interval

def log_upload_trigger(buffer_size: int, threshold: int) -> None:
    """
    Log when Azure upload is triggered.
    
    Args:
        buffer_size: Current buffer size
        threshold: Upload threshold
    """
    logger.warning(f"🚀 AZURE UPLOAD TRIGGERED: Buffer reached {buffer_size} circuits (threshold: {threshold})")

def log_final_upload(buffer_size: int) -> None:
    """
    Log when final Azure upload is triggered during shutdown.
    
    Args:
        buffer_size: Current buffer size
    """
    logger.warning(f"🏁 FINAL AZURE UPLOAD: Processing {buffer_size} remaining circuits before shutdown")