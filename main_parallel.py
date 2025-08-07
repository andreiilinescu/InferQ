#!/usr/bin/env python3
"""
High-Performance Parallel Quantum Circuit Processing Pipeline
Optimized for Intel Xeon E5-6248R 24C 3.0GHz with 185GB RAM

Features:
- Parallel pipeline execution
- Minimal logging (warnings and essential messages only)
- Continuous operation
- Efficient memory usage
- Local disk storage priority
"""

import os
import sys
import time
import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import signal
import json
from datetime import datetime
import psutil
import numpy as np

# Suppress numpy array printing to stdout
np.set_printoptions(suppress=True, threshold=0)

# Import pipeline components
from generators.circuit_merger import CircuitMerger
from generators.lib.generator import BaseParams
from utils.save_utils import save_circuit_locally, save_circuit_metadata_to_table, upload_circuit_blob
from utils.azure_connection import AzureConnection
from feature_extractors.extractors import extract_features
from simulators.simulate import QuantumSimulator
from simulators.simulation_utils import process_simulation_data_for_features

# Configure minimal logging - only warnings and essential messages
# Create file handler with buffering
file_handler = logging.FileHandler('pipeline.log')
file_handler.setLevel(logging.WARNING)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Configure root logger
logging.basicConfig(
    level=logging.WARNING,
    handlers=[file_handler, console_handler]
)

# Suppress ALL verbose logging - comprehensive list
verbose_loggers = [
    'qiskit', 'qiskit.passmanager', 'qiskit.compiler', 'qiskit.transpiler', 'qiskit_aer',
    'azure.core', 'azure.storage', 'azure.data.tables', 'azure.storage.blob',
    'azure.core.pipeline.policies.http_logging_policy',
    # 'simulators.simulate', 'simulators.simulation_utils',  # Temporarily enable for debugging
    'feature_extractors.extractors', 'feature_extractors.static_features',
    'feature_extractors.graph_features', 'feature_extractors.dynamic_features', 'feature_extractors.graphs',
    # 'generators.circuit_merger', 
    'utils.local_storage', 'utils.table_storage',
    'utils.blob_storage', 'utils.azure_connection', 'utils.save_utils',
    'rustworkx', 'rx',  # Suppress rustworkx matrix outputs
    '__main__'  # Suppress main module info logging
]

for logger_name in verbose_loggers:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

# Set root logger to WARNING to catch a

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_flag = mp.Value('i', 0)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.warning(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_flag.value = 1

def run_single_pipeline(worker_id: int, seed_offset: int) -> dict:
    """
    Run a single pipeline iteration optimized for performance.
    
    Args:
        worker_id: Worker process ID
        seed_offset: Seed offset for randomization
        
    Returns:
        Dictionary with pipeline results including circuit data for remote upload
    """
    try:
        # Use worker-specific seed for reproducibility
        seed = 42 + seed_offset + worker_id * 1000
        
        # Initialize components (lightweight initialization)
        base_params = BaseParams(
            max_qubits=8, min_qubits=2, max_depth=1000, min_depth=10, 
            seed=seed, measure=False
        )
        circuit_merger = CircuitMerger(base_params=base_params)
        quantum_simulator = QuantumSimulator(seed=seed)
        
        # Step 1: Generate circuit
        circuit = circuit_merger.generate_hierarchical_circuit()
        
        # Step 2: Extract features
        features = extract_features(circuit=circuit)
        
        # Step 3: Run simulations
        simulation_results = quantum_simulator.simulate_all_methods(circuit)
        
        # Step 4: Process simulation data
        combined_features = process_simulation_data_for_features(simulation_results, features)
        
        # Step 5: Save locally (prioritize local storage for performance)
        qpy_hash, saved_features, written = save_circuit_locally(
            circuit, combined_features, Path("./circuits_hpc/")
        )
        
        return {
            'success': True,
            'worker_id': worker_id,
            'circuit_hash': qpy_hash,
            'circuit_qubits': circuit.num_qubits,
            'circuit_depth': circuit.depth(),
            'circuit_size': circuit.size(),
            'features_count': len(combined_features),
            'written': written,
            'timestamp': datetime.now().isoformat(),
            # Include data for remote upload
            'circuit': circuit,
            'features': saved_features,
            'serialization_method': saved_features.get('serialization_method', 'qpy')
        }
        
    except Exception as e:
        return {
            'success': False,
            'worker_id': worker_id,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def cleanup_old_circuits(circuits_dir: Path, max_age_hours: int = 24) -> dict:
    """
    Clean up old circuit files to free disk space.
    
    Args:
        circuits_dir: Directory containing circuit files
        max_age_hours: Maximum age in hours before deletion
        
    Returns:
        Dictionary with cleanup statistics
    """
    if not circuits_dir.exists():
        return {'deleted': 0, 'freed_gb': 0}
    
    deleted_count = 0
    freed_bytes = 0
    cutoff_time = time.time() - (max_age_hours * 3600)
    
    try:
        for circuit_dir in circuits_dir.iterdir():
            if circuit_dir.is_dir():
                # Check if directory is old enough
                dir_mtime = circuit_dir.stat().st_mtime
                if dir_mtime < cutoff_time:
                    # Calculate size before deletion
                    dir_size = sum(f.stat().st_size for f in circuit_dir.rglob('*') if f.is_file())
                    
                    # Delete the directory
                    import shutil
                    shutil.rmtree(circuit_dir)
                    
                    deleted_count += 1
                    freed_bytes += dir_size
    
    except Exception as e:
        logger.warning(f"Cleanup error: {e}")
    
    freed_gb = freed_bytes / (1024**3)
    return {'deleted': deleted_count, 'freed_gb': freed_gb}

def upload_batch_to_azure(circuit_batch: list, azure_conn: AzureConnection) -> dict:
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
    
    try:
        container_client = azure_conn.get_container_client()
        table_client = azure_conn.get_circuits_table_client()
        
        for result in circuit_batch:
            if not result.get('success') or not result.get('written'):
                continue
                
            try:
                circuit = result['circuit']
                features = result['features']
                qpy_hash = result['circuit_hash']
                serialization_method = result['serialization_method']
                
                # Upload to blob storage
                blob_path = upload_circuit_blob(
                    container_client, circuit, qpy_hash, serialization_method
                )
                features["blob_path"] = blob_path.split("circuits/")[1] if "circuits/" in blob_path else blob_path
                
                # Save metadata to table storage
                table_success = save_circuit_metadata_to_table(table_client, features)
                
                if table_success:
                    uploaded += 1
                else:
                    failed += 1
                    
            except Exception as e:
                failed += 1
                logger.warning(f"Failed to upload circuit {result.get('circuit_hash', 'unknown')}: {e}")
                
    except Exception as e:
        logger.warning(f"Batch upload failed: {e}")
        return {'uploaded': 0, 'failed': len(circuit_batch), 'error': str(e)}
    
    return {'uploaded': uploaded, 'failed': failed}

def monitor_system_resources():
    """Monitor system resources and return current usage"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('.')
    
    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'memory_available_gb': memory.available / (1024**3),
        'disk_free_gb': disk.free / (1024**3)
    }

def run_parallel_pipeline(num_workers: int = None, max_iterations: int = None, 
                         batch_size: int = 50, azure_upload_interval: int = 100):
    """
    Run parallel pipeline with continuous operation and optimized remote storage.
    
    Args:
        num_workers: Number of parallel workers (default: CPU count - 2)
        max_iterations: Maximum iterations (None for infinite)
        batch_size: Circuits per batch before status update
        azure_upload_interval: Upload to Azure every N circuits
    """
    
    # Set optimal worker count for 24-core system
    if num_workers is None:
        num_workers = min(22, mp.cpu_count() - 2)  # Leave 2 cores for system
    
    logger.warning(f"🚀 Starting parallel pipeline with {num_workers} workers")
    logger.warning(f"System: {mp.cpu_count()} cores, {psutil.virtual_memory().total / (1024**3):.1f}GB RAM")
    
    # Initialize Azure connection for remote storage
    azure_conn = None
    try:
        azure_conn = AzureConnection()
        logger.warning("✓ Azure connection established for remote storage")
    except Exception as e:
        logger.warning(f"⚠️  Azure connection failed: {e}")
        logger.warning("⚠️  Remote storage disabled - LOCAL ONLY mode")
    
    # Create local storage directory
    Path("./circuits_hpc").mkdir(exist_ok=True)
    
    # Statistics tracking
    stats = {
        'total_processed': 0,
        'successful': 0,
        'failed': 0,
        'uploaded_to_azure': 0,
        'upload_failures': 0,
        'start_time': time.time(),
        'last_azure_upload': 0
    }
    
    # Buffer for Azure uploads
    upload_buffer = []
    iteration = 0
    
    try:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            
            while max_iterations is None or iteration < max_iterations:
                if shutdown_flag.value:
                    logger.warning("Shutdown flag detected, stopping pipeline...")
                    break
                
                # Submit batch of work
                futures = []
                for i in range(batch_size):
                    if shutdown_flag.value:
                        break
                    future = executor.submit(run_single_pipeline, i % num_workers, iteration * batch_size + i)
                    futures.append(future)
                
                # Process completed work and collect for Azure upload
                batch_successful = 0
                batch_failed = 0
                batch_results = []
                
                for future in as_completed(futures):
                    if shutdown_flag.value:
                        break
                        
                    result = future.result()
                    stats['total_processed'] += 1
                    
                    if result['success']:
                        stats['successful'] += 1
                        batch_successful += 1
                        batch_results.append(result)
                        
                        # Add to upload buffer if Azure is available
                        if azure_conn and result.get('written'):
                            upload_buffer.append(result)
                    else:
                        stats['failed'] += 1
                        batch_failed += 1
                        logger.warning(f"Pipeline failed: {result.get('error', 'Unknown error')}")
                
                # Upload to Azure when buffer reaches threshold
                if azure_conn and len(upload_buffer) >= azure_upload_interval:
                    logger.warning(f"📤 Uploading {len(upload_buffer)} circuits to Azure...")
                    
                    upload_stats = upload_batch_to_azure(upload_buffer, azure_conn)
                    stats['uploaded_to_azure'] += upload_stats['uploaded']
                    stats['upload_failures'] += upload_stats['failed']
                    
                    if upload_stats['uploaded'] > 0:
                        logger.warning(f"✓ Uploaded {upload_stats['uploaded']} circuits to Azure")
                    if upload_stats['failed'] > 0:
                        logger.warning(f"⚠️  {upload_stats['failed']} Azure uploads failed")
                    
                    # Clear buffer
                    upload_buffer = []
                    stats['last_azure_upload'] = stats['total_processed']
                    
                    # Cleanup old local files after successful upload
                    if stats['total_processed'] % 1000 == 0:  # Every 1000 circuits
                        cleanup_stats = cleanup_old_circuits(Path("./circuits_hpc"), max_age_hours=24)
                        if cleanup_stats['deleted'] > 0:
                            logger.warning(f"🧹 Cleaned up {cleanup_stats['deleted']} old circuits, freed {cleanup_stats['freed_gb']:.1f}GB")
                
                # Status update every batch
                elapsed = time.time() - stats['start_time']
                rate = stats['total_processed'] / elapsed * 60 if elapsed > 0 else 0
                
                # Monitor system resources
                resources = monitor_system_resources()
                
                # Enhanced status with Azure upload info
                azure_status = ""
                if azure_conn:
                    azure_status = f" | Azure: {stats['uploaded_to_azure']}↑ | Buffer: {len(upload_buffer)}"
                
                logger.warning(
                    f"Batch {iteration + 1}: {batch_successful}✓/{batch_failed}✗ | "
                    f"Total: {stats['successful']}✓/{stats['failed']}✗ | "
                    f"Rate: {rate:.1f}/min | "
                    f"CPU: {resources['cpu_percent']:.1f}% | "
                    f"RAM: {resources['memory_percent']:.1f}% | "
                    f"Disk: {resources['disk_free_gb']:.1f}GB{azure_status}"
                )
                
                iteration += 1
                
                # Brief pause to prevent system overload
                time.sleep(0.05)  # Reduced pause for higher throughput
    
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
    finally:
        # Upload remaining circuits in buffer
        if azure_conn and upload_buffer:
            logger.warning(f"📤 Final upload: {len(upload_buffer)} circuits to Azure...")
            upload_stats = upload_batch_to_azure(upload_buffer, azure_conn)
            stats['uploaded_to_azure'] += upload_stats['uploaded']
            stats['upload_failures'] += upload_stats['failed']
        
        # Final statistics
        elapsed = time.time() - stats['start_time']
        rate = stats['total_processed'] / elapsed * 60 if elapsed > 0 else 0
        
        logger.warning("=" * 80)
        logger.warning("PIPELINE COMPLETED")
        logger.warning(f"Total processed: {stats['total_processed']}")
        logger.warning(f"Successful: {stats['successful']}")
        logger.warning(f"Failed: {stats['failed']}")
        if stats['total_processed'] > 0:
            logger.warning(f"Success rate: {stats['successful']/stats['total_processed']*100:.1f}%")
        if azure_conn:
            logger.warning(f"Uploaded to Azure: {stats['uploaded_to_azure']}")
            logger.warning(f"Upload failures: {stats['upload_failures']}")
            total_uploads = stats['uploaded_to_azure'] + stats['upload_failures']
            if total_uploads > 0:
                logger.warning(f"Upload success rate: {stats['uploaded_to_azure']/total_uploads*100:.1f}%")
        logger.warning(f"Average rate: {rate:.1f} circuits/minute")
        logger.warning(f"Total runtime: {elapsed/3600:.1f} hours")
        logger.warning("=" * 80)

def main():
    """Main entry point with command line argument support"""
    import argparse
    
    parser = argparse.ArgumentParser(description='High-Performance Quantum Circuit Pipeline')
    parser.add_argument('--workers', type=int, default=None, 
                       help='Number of parallel workers (default: CPU count - 2)')
    parser.add_argument('--iterations', type=int, default=None,
                       help='Maximum iterations (default: infinite)')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Circuits per batch (default: 100)')
    parser.add_argument('--azure-interval', type=int, default=1000,
                       help='Azure upload interval (default: 1000)')
    parser.add_argument('--profile', action='store_true',
                       help='Enable performance profiling')
    
    args = parser.parse_args()
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Performance profiling (optional)
    if args.profile:
        import cProfile
        import pstats
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            run_parallel_pipeline(
                num_workers=args.workers,
                max_iterations=args.iterations,
                batch_size=args.batch_size,
                azure_upload_interval=args.azure_interval
            )
        finally:
            profiler.disable()
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            stats.print_stats(20)  # Top 20 functions
    else:
        run_parallel_pipeline(
            num_workers=args.workers,
            max_iterations=args.iterations,
            batch_size=args.batch_size,
            azure_upload_interval=args.azure_interval
        )

if __name__ == "__main__":
    main()