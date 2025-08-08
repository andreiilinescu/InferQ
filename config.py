"""
Quantum Circuit Pipeline Configuration
Centralized configuration for all pipeline components
"""

import os
import multiprocessing as mp
from pathlib import Path

class PipelineConfig:
    """Central configuration for the quantum circuit pipeline."""
    
    def __init__(self):
        # Base paths
        self.project_root = Path(__file__).parent
        self.circuits_dir = self.project_root / "circuits"
        self.logs_dir = self.project_root / "logs"
        
        # Ensure directories exist
        self.circuits_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
    
    # System Configuration
    @property
    def cpu_cores(self):
        """Available CPU cores."""
        return mp.cpu_count()
    
    @property
    def optimal_workers(self):
        """Optimal number of worker processes."""
        return max(1, self.cpu_cores - 2)
    
    # Pipeline Defaults
    PIPELINE_DEFAULTS = {
        'workers': None,  # Auto-detect
        'batch_size': 2,
        'azure_upload_interval': 2,
        'max_iterations': None,  # Infinite
    }
    
    # Circuit Generation
    CIRCUIT_GENERATION = {
        'max_qubits': 5,
        'min_qubits': 1,
        'max_depth': 2000,
        'min_depth': 1,
        'measure': False,
        'seed': 21384,
        'stopping_probability': 0.3,  # Probability to stop adding generators
        'max_generators': 5,  # Maximum generators in hierarchy
    }
    
    # Simulation Configuration
    SIMULATION = {
        'shots': None,  # Exact simulation
        'seed': 21384,
        'timeout_seconds': 300,  # 5 minutes per circuit
    }
    
    # Storage Configuration
    STORAGE = {
        'local_circuits_dir': 'circuits',
        'cache_file': 'circuit_hashes_cache.json',
        'max_local_storage_gb': 50,
    }
    
    # Azure Configuration
    AZURE = {
        'container_name': 'circuits',
        'table_name': 'circuits',
    }
    
    # Logging Configuration
    LOGGING = {
        'level': 'WARNING',  # Minimal for performance
        'format': '%(asctime)s - %(levelname)s - %(message)s',
        'file_max_size_mb': 100,
        'backup_count': 5,
        'console_output': True,
    }
    
    # Performance Optimization
    PERFORMANCE = {
        'numpy_threads': 4,
        'gc_threshold': 1000,
        'process_priority': -5,  # Higher priority (Unix)
        'memory_limit_percent': 80,
    }
    
    # Duplicate Detection
    DUPLICATE_DETECTION = {
        'enabled': True,
        'cache_validation': True,
        'session_coordination': True,
        'batch_sync_interval': 10,  # Sync every 10 batches
    }

    def get_env_or_default(self, key, default=None, type_cast=None):
        """Get environment variable or return default."""
        value = os.getenv(key, default)
        if value is not None and type_cast:
            try:
                return type_cast(value)
            except (ValueError, TypeError):
                return default
        return value
    
    def get_pipeline_config(self):
        """Get pipeline configuration with environment variable overrides."""
        return {
            'workers': self.get_env_or_default('WORKERS', self.optimal_workers, int),
            'batch_size': self.get_env_or_default('BATCH_SIZE', self.PIPELINE_DEFAULTS['batch_size'], int),
            'azure_upload_interval': self.get_env_or_default('AZURE_INTERVAL', self.PIPELINE_DEFAULTS['azure_upload_interval'], int),
            'max_iterations': self.get_env_or_default('ITERATIONS', self.PIPELINE_DEFAULTS['max_iterations'], int),
        }
    
    def get_circuit_config(self):
        """Get circuit generation configuration."""
        return {
            'max_qubits': self.get_env_or_default('MAX_QUBITS', self.CIRCUIT_GENERATION['max_qubits'], int),
            'min_qubits': self.get_env_or_default('MIN_QUBITS', self.CIRCUIT_GENERATION['min_qubits'], int),
            'max_depth': self.get_env_or_default('MAX_DEPTH', self.CIRCUIT_GENERATION['max_depth'], int),
            'min_depth': self.get_env_or_default('MIN_DEPTH', self.CIRCUIT_GENERATION['min_depth'], int),
            'measure': self.get_env_or_default('MEASURE', self.CIRCUIT_GENERATION['measure'], bool),
            'seed': self.get_env_or_default('SEED', self.CIRCUIT_GENERATION['seed'], int),
            'stopping_probability': self.get_env_or_default('STOPPING_PROB', self.CIRCUIT_GENERATION['stopping_probability'], float),
            'max_generators': self.get_env_or_default('MAX_GENERATORS', self.CIRCUIT_GENERATION['max_generators'], int),
        }
    
    def apply_performance_optimizations(self):
        """Apply system-level performance optimizations."""
        # Set thread limits to avoid oversubscription
        thread_count = str(self.PERFORMANCE['numpy_threads'])
        os.environ['OMP_NUM_THREADS'] = thread_count
        os.environ['OPENBLAS_NUM_THREADS'] = thread_count
        os.environ['MKL_NUM_THREADS'] = thread_count
        os.environ['NUMEXPR_NUM_THREADS'] = thread_count
        
        # Unbuffered Python output
        os.environ['PYTHONUNBUFFERED'] = '1'
        
        # Garbage collection optimization
        import gc
        gc.set_threshold(self.PERFORMANCE['gc_threshold'])
        
        # Process priority (Unix systems only)
        try:
            os.nice(self.PERFORMANCE['process_priority'])
        except (OSError, AttributeError):
            pass  # Not supported on all systems
    
    def get_azure_config(self):
        """Get Azure configuration."""
        return {
            'connection_string': self.get_env_or_default('AZURE_STORAGE_CONNECTION_STRING'),
            'account_name': self.get_env_or_default('AZURE_STORAGE_ACCOUNT_NAME'),
            'account_key': self.get_env_or_default('AZURE_STORAGE_ACCOUNT_KEY'),
            'container_name': self.get_env_or_default('AZURE_CONTAINER', self.AZURE['container_name']),
            'table_name': self.get_env_or_default('AZURE_TABLE', self.AZURE['table_name']),
        }
    
    def print_config_summary(self):
        """Print a summary of current configuration."""
        pipeline_config = self.get_pipeline_config()
        circuit_config = self.get_circuit_config()
        azure_config = self.get_azure_config()
        
        print("Pipeline Configuration Summary")
        print("=" * 50)
        print(f"Workers: {pipeline_config['workers']}")
        print(f"Batch size: {pipeline_config['batch_size']}")
        print(f"Azure interval: {pipeline_config['azure_upload_interval']}")
        print(f"Max iterations: {pipeline_config['max_iterations'] or 'Infinite'}")
        print()
        print(f"Circuit qubits: {circuit_config['min_qubits']}-{circuit_config['max_qubits']}")
        print(f"Circuit depth: {circuit_config['min_depth']}-{circuit_config['max_depth']}")
        print(f"Stopping probability: {circuit_config['stopping_probability']}")
        print(f"Max generators: {circuit_config['max_generators']}")
        print(f"Seed: {circuit_config['seed']}")
        print()
        print(f"Azure enabled: {azure_config['enabled']}")
        print(f"Local storage: {self.circuits_dir}")
        print("=" * 50)

# Global configuration instance
config = PipelineConfig()

# Convenience functions for common use cases
def get_pipeline_config():
    """Get pipeline configuration."""
    return config.get_pipeline_config()

def get_circuit_config():
    """Get circuit generation configuration."""
    return config.get_circuit_config()

def get_azure_config():
    """Get Azure configuration."""
    return config.get_azure_config()

def apply_optimizations():
    """Apply performance optimizations."""
    config.apply_performance_optimizations()

if __name__ == "__main__":
    # Print configuration when run directly
    config.print_config_summary()