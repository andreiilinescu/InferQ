# Pipeline Scripts

This directory contains modular scripts for running the quantum circuit processing pipeline in different modes.

## Scripts Overview

### Core Utilities
- `system_info.sh` - System information detection and environment setup
- `azure_check.sh` - Azure connectivity validation
- `pipeline_monitor.sh` - Process monitoring and management utilities

### Pipeline Runners

#### `run_parallel.sh` - High-Performance Runner
Full production pipeline optimized for HPC systems with maximum throughput.
```bash
# Default HPC run (auto-detects optimal settings)
./scripts/run_parallel.sh

# Custom HPC configuration
WORKERS=20 BATCH_SIZE=300 AZURE_INTERVAL=200 ./scripts/run_parallel.sh
```

#### `run_light.sh` - Light Runner
Conservative pipeline for testing or resource-limited environments.
```bash
# Default light run
./scripts/run_light.sh

# Custom light configuration
WORKERS=2 BATCH_SIZE=20 ./scripts/run_light.sh
```

## Environment Variables

All scripts support these environment variables for customization:

- `WORKERS` - Number of parallel workers (default: auto-detect)
- `ITERATIONS` - Maximum iterations (default: infinite)
- `BATCH_SIZE` - Circuits per batch (default: 100)
- `AZURE_INTERVAL` - Azure upload interval (default: 1000)

## Usage Examples

### Light Testing/Development
```bash
# Conservative run for testing
./scripts/run_light.sh
```

### Full HPC Production
```bash
# Maximum performance production run
./scripts/run_parallel.sh
```

### Custom Configurations
```bash
# Ultra high-throughput HPC
WORKERS=24 BATCH_SIZE=500 AZURE_INTERVAL=100 ./scripts/run_parallel.sh

# Minimal resource usage
WORKERS=2 BATCH_SIZE=10 AZURE_INTERVAL=5000 ./scripts/run_light.sh
```

## Logs and Output

All scripts create logs in the `logs/` directory with timestamps:
- `parallel_pipeline_YYYYMMDD_HHMMSS.log` (HPC mode)
- `light_pipeline_YYYYMMDD_HHMMSS.log` (Light mode)

## System Requirements

- Python 3.8+
- Virtual environment recommended
- Cross-platform (Linux/macOS)
- Azure credentials (optional, falls back to local-only mode)

## Troubleshooting

1. **Permission denied**: Make scripts executable
   ```bash
   chmod +x scripts/*.sh
   ```

2. **Azure connection issues**: Check environment variables
   ```bash
   ./scripts/azure_check.sh
   ```

3. **Performance issues**: Use system monitoring
   ```bash
   htop  # or top on macOS
   ```

4. **Pipeline stuck**: Check recent log activity
   ```bash
   tail -f logs/parallel_pipeline_*.log
   ```