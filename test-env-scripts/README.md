# DelftBlue Environment Test Suite

Comprehensive test suite to verify that your environment is ready for running quantum circuit processing on DelftBlue HPC.

## Quick Start

```bash
# Make scripts executable
chmod +x test-env-scripts/*.sh

# Run all tests
./test-env-scripts/run_all_tests.sh

# Or run individual tests
python3 test-env-scripts/01_test_python.py
```

## Test Overview

### 1. Python Environment (`01_test_python.py`)
- ✅ Python version compatibility (3.8+)
- ✅ Virtual environment setup
- ✅ Python path configuration
- ✅ Basic standard library imports
- ✅ File system permissions

### 2. Package Installation (`02_test_packages.py`)
- ✅ Critical packages (Qiskit, NumPy, SciPy, etc.)
- ✅ Package version compatibility
- ✅ Optional packages (Azure, monitoring tools)
- ✅ Basic quantum functionality test

### 3. Azure Connectivity (`03_test_azure.py`)
- ✅ Azure package imports
- ✅ Environment variable configuration
- ✅ Connection to Azure services
- ✅ Read/write permissions test

### 4. System Resources (`04_test_system.py`)
- ✅ CPU cores and performance
- ✅ Memory availability
- ✅ Disk space and I/O speed
- ✅ Environment variables
- ✅ Quantum computing performance

### 5. Pipeline Integration (`05_test_pipeline.py`)
- ✅ Configuration module
- ✅ Circuit generation
- ✅ Feature extraction
- ✅ Quantum simulation
- ✅ Local storage
- ✅ Full pipeline integration

## Usage Examples

### Run All Tests
```bash
./test-env-scripts/run_all_tests.sh
```

### Quick Test (Critical Only)
```bash
./test-env-scripts/run_all_tests.sh --quick
```

### Individual Tests
```bash
# Test Python environment
python3 test-env-scripts/01_test_python.py

# Test package installation
python3 test-env-scripts/02_test_packages.py

# Test Azure connectivity
python3 test-env-scripts/03_test_azure.py

# Test system resources
python3 test-env-scripts/04_test_system.py

# Test pipeline integration
python3 test-env-scripts/05_test_pipeline.py
```

## Test Results

### Exit Codes
- `0`: All tests passed
- `1`: Some tests failed

### Output Files
- `test_report_YYYYMMDD_HHMMSS.txt`: Detailed test report
- Console output with colored status indicators

### Status Indicators
- ✅ **PASS**: Test completed successfully
- ❌ **FAIL**: Test failed (critical issue)
- ⚠️  **SKIP**: Test skipped (non-critical)

## Common Issues and Solutions

### Python Version Issues
```bash
# If Python 3.8 is not available
module load python/3.8.12

# Check available Python modules
module avail python
```

### Package Installation Issues
```bash
# Install Python 3.8 compatible packages
pip install -r requirements_delftblue_py38.txt

# If virtual environment issues
rm -rf .venv
python -m venv .venv --system-site-packages
source .venv/bin/activate
```

### Azure Configuration Issues
```bash
# Set Azure storage account and key (recommended)
export AZURE_STORAGE_ACCOUNT="your_account_name"
export AZURE_STORAGE_ACCOUNT_KEY="your_account_key"

# Or set SAS token and container URL
export AZURE_STORAGE_SAS_TOKEN="?sp=racwdli&st=..."
export AZURE_CONTAINER_SAS_URL="https://account.blob.core.windows.net/container?..."

# Optional: Set connection string (fallback)
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
```

### System Resource Issues
```bash
# Check available resources
sinfo
squeue -u $USER

# Request appropriate resources in Slurm script
#SBATCH --cpus-per-task=24
#SBATCH --mem=180G
```

### Pipeline Issues
```bash
# Check project structure
ls -la generators/ feature_extractors/ simulators/ utils/

# Verify Python path
python -c "import sys; print('\n'.join(sys.path))"
```

## Integration with HPC Workflow

### Before Submitting Jobs
1. Run the test suite on login node:
   ```bash
   ./test-env-scripts/run_all_tests.sh
   ```

2. Fix any critical issues identified

3. Submit your job:
   ```bash
   sbatch submit_delftblue.sh
   ```

### In Slurm Jobs
The test scripts can also be run within Slurm jobs to verify the compute node environment:

```bash
#SBATCH --job-name=env_test
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G

# Load modules
module load python/3.8.12

# Activate environment
source .venv/bin/activate

# Run tests
./test-env-scripts/run_all_tests.sh --quick
```

## Troubleshooting

### Test Failures
1. **Python Environment**: Check Python version and virtual environment
2. **Packages**: Install missing packages or fix version conflicts
3. **Azure**: Configure credentials or run in local-only mode
4. **System**: Check resource availability and permissions
5. **Pipeline**: Verify project structure and imports

### Performance Issues
- Reduce circuit size for testing: `MAX_QUBITS=3`
- Use fewer simulation shots: `SHOTS=100`
- Increase timeouts: `SIM_TIMEOUT=600`

### Permission Issues
```bash
# Make scripts executable
chmod +x test-env-scripts/*.sh

# Check write permissions
touch test_file && rm test_file
```

## Support

If tests continue to fail:

1. Check the generated test report for detailed error messages
2. Verify DelftBlue module availability: `module avail`
3. Check system status: `sinfo` and `squeue`
4. Review DelftBlue documentation: https://doc.dhpc.tudelft.nl/delftblue/

## Files in This Directory

- `01_test_python.py` - Python environment verification
- `02_test_packages.py` - Package installation verification  
- `03_test_azure.py` - Azure connectivity verification
- `04_test_system.py` - System resources verification
- `05_test_pipeline.py` - Pipeline integration verification
- `run_all_tests.sh` - Master test runner script
- `README.md` - This documentation file