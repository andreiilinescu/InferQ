"""
High-Performance Computing Configuration
Optimized for Intel Xeon E5-6248R 24C 3.0GHz, 185GB RAM

This configuration file contains optimized settings for running the quantum
circuit processing pipeline on high-performance hardware.
"""

import os
import multiprocessing as mp

# Hardware specifications
HARDWARE_SPECS = {
    'cpu_cores': 24,
    'cpu_model': 'Intel Xeon E5-6248R',
    'cpu_frequency': '3.0GHz',
    'total_memory_gb': 185,
    'disk_space_gb': 150
}

# Parallel processing configuration
PARALLEL_CONFIG = {
    # Use 22 cores (leave 2 for system processes)
    'max_workers': min(22, mp.cpu_count() - 2),
    
    # Batch size optimized for memory usage
    'batch_size': 50,  # Process 50 circuits per batch
    
    # Memory management
    'max_memory_usage_percent': 80,  # Don't exceed 80% RAM usage
    'memory_check_interval': 100,   # Check memory every 100 circuits
    
    # Process pool settings
    'process_timeout': 300,  # 5 minutes per circuit max
    'max_tasks_per_child': 1000,  # Restart workers after 1000 tasks
}

# Circuit generation parameters
CIRCUIT_CONFIG = {
    'max_qubits': 12,      # Increased for HPC
    'min_qubits': 2,
    'max_depth': 2000,     # Increased depth for complex circuits
    'min_depth': 10,
    'measure': False,      # Avoid measurements for better simulation compatibility
}

# Simulation configuration
SIMULATION_CONFIG = {
    # Prioritize faster simulation methods for high throughput
    'priority_methods': ['statevector', 'matrix_product_state', 'density_matrix'],
    
    # Skip slow methods for large circuits
    'skip_unitary_above_qubits': 8,  # Unitary simulation becomes very slow
    'skip_density_matrix_above_qubits': 10,
    
    # Memory limits per simulation
    'max_simulation_memory_gb': 20,
}

# Storage configuration
STORAGE_CONFIG = {
    # Local storage settings (temporary buffer)
    'local_storage_path': './circuits_hpc',
    'max_local_storage_gb': 50,   # Reduced - use as temporary buffer
    
    # Azure upload settings (optimized for HPC)
    'azure_upload_enabled': True,
    'azure_batch_size': 100,      # Upload every 100 circuits (more frequent)
    'azure_upload_workers': 6,    # More parallel Azure uploads
    'azure_retry_attempts': 3,
    'azure_timeout_seconds': 300, # 5 minute timeout per upload
    
    # Cleanup settings (aggressive for HPC)
    'cleanup_old_circuits': True,
    'max_circuit_age_hours': 24,  # Delete local circuits after 24 hours
    'cleanup_interval': 1000,     # Check for cleanup every 1000 circuits
}

# Logging configuration
LOGGING_CONFIG = {
    'level': 'WARNING',  # Minimal logging for performance
    'file': 'pipeline_hpc.log',
    'max_file_size_mb': 100,
    'backup_count': 5,
    
    # Status reporting
    'status_interval': 100,       # Report status every 100 circuits
    'detailed_stats_interval': 1000,  # Detailed stats every 1000 circuits
}

# Performance monitoring
MONITORING_CONFIG = {
    'enable_profiling': False,    # Disable by default for performance
    'resource_monitoring': True, # Monitor CPU/RAM/disk usage
    'performance_log': 'performance.json',
    
    # Alerts
    'cpu_alert_threshold': 95,    # Alert if CPU > 95%
    'memory_alert_threshold': 90, # Alert if RAM > 90%
    'disk_alert_threshold': 95,   # Alert if disk > 95%
}

# Optimization flags
OPTIMIZATION_CONFIG = {
    # Python optimizations
    'use_multiprocessing': True,
    'optimize_imports': True,
    'gc_threshold': 1000,  # Garbage collection threshold
    
    # Qiskit optimizations
    'qiskit_parallel_threshold': 14,  # Use parallel for circuits > 14 qubits
    'transpiler_optimization_level': 1,  # Balance speed vs optimization
    
    # NumPy optimizations
    'numpy_threads': 4,  # Limit NumPy threads to avoid oversubscription
}

def get_optimal_config():
    """
    Return optimized configuration based on current system resources.
    """
    import psutil
    
    # Adjust based on available memory
    available_memory_gb = psutil.virtual_memory().available / (1024**3)
    
    config = {
        'parallel': PARALLEL_CONFIG.copy(),
        'circuit': CIRCUIT_CONFIG.copy(),
        'simulation': SIMULATION_CONFIG.copy(),
        'storage': STORAGE_CONFIG.copy(),
        'logging': LOGGING_CONFIG.copy(),
        'monitoring': MONITORING_CONFIG.copy(),
        'optimization': OPTIMIZATION_CONFIG.copy(),
    }
    
    # Adjust batch size based on available memory
    if available_memory_gb < 50:
        config['parallel']['batch_size'] = 25
        config['circuit']['max_qubits'] = 8
    elif available_memory_gb > 150:
        config['parallel']['batch_size'] = 100
        config['circuit']['max_qubits'] = 15
    
    return config

def apply_optimizations():
    """
    Apply system-level optimizations for high-performance execution.
    """
    import gc
    
    # Set environment variables for optimal performance
    os.environ['OMP_NUM_THREADS'] = str(OPTIMIZATION_CONFIG['numpy_threads'])
    os.environ['OPENBLAS_NUM_THREADS'] = str(OPTIMIZATION_CONFIG['numpy_threads'])
    os.environ['MKL_NUM_THREADS'] = str(OPTIMIZATION_CONFIG['numpy_threads'])
    os.environ['NUMEXPR_NUM_THREADS'] = str(OPTIMIZATION_CONFIG['numpy_threads'])
    
    # Garbage collection optimization
    gc.set_threshold(OPTIMIZATION_CONFIG['gc_threshold'])
    
    # Set process priority (Unix systems)
    try:
        os.nice(-5)  # Higher priority
    except (OSError, AttributeError):
        pass  # Not supported on all systems

if __name__ == "__main__":
    # Print configuration summary
    config = get_optimal_config()
    print("High-Performance Configuration Summary:")
    print("=" * 50)
    print(f"Workers: {config['parallel']['max_workers']}")
    print(f"Batch size: {config['parallel']['batch_size']}")
    print(f"Max qubits: {config['circuit']['max_qubits']}")
    print(f"Max depth: {config['circuit']['max_depth']}")
    print(f"Local storage: {config['storage']['local_storage_path']}")
    print(f"Azure uploads: {config['storage']['azure_upload_enabled']}")
    print("=" * 50)