#!/bin/bash
#SBATCH --job-name=inferq_test
#SBATCH --partition=compute
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=2GB
#SBATCH --account=research-eemcs-qce

# Output and error files
#SBATCH --output=logs/test_%j.out
#SBATCH --error=logs/test_%j.err

# Load required modules
module load 2023r1
module load python/3.12.6

# Print basic job info
echo "=========================================="
echo "DelftBlue Test Job"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Start Time: $(date)"
echo "Working Directory: $(pwd)"
echo "=========================================="

# Create logs directory
mkdir -p logs

# Check Python environment
echo "Python environment check:"
python3 --version
python3 -c "import sys; print(f'Python path: {sys.executable}')"

# Test basic imports
echo "Testing package imports:"
python3 -c "
try:
    import numpy as np
    print('✓ NumPy available')
except ImportError as e:
    print(f'✗ NumPy error: {e}')

try:
    import qiskit
    print('✓ Qiskit available')
except ImportError as e:
    print(f'✗ Qiskit error: {e}')
"

echo "=========================================="
echo "Running main.py once..."

# Set Python path and run main.py once
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

python3 main.py

EXIT_CODE=$?

echo "=========================================="
echo "Test completed with exit code: $EXIT_CODE"
echo "End Time: $(date)"
echo "=========================================="

exit $EXIT_CODE