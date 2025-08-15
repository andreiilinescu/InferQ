#!/bin/bash
#SBATCH --job-name=inferq_quantum
#SBATCH --partition=compute
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=180G
#SBATCH --account=research-eemcs-qce

# Output and error files
#SBATCH --output=logs/slurm_%j.out
#SBATCH --error=logs/slurm_%j.err

# Email notifications (optional - uncomment and set your email)
# #SBATCH --mail-type=BEGIN,END,FAIL
# #SBATCH --mail-user=your.email@tudelft.nl

# Load required modules for DelftBlue
module purge
module load 2023r1
module load python/3.11.3

# Print job information
echo "=========================================="
echo "DelftBlue HPC Job Information"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: $SLURM_JOB_NAME"
echo "Node: $SLURMD_NODENAME"
echo "Start Time: $(date)"
echo "Working Directory: $(pwd)"
echo "CPUs per task: $SLURM_CPUS_PER_TASK"
echo "Memory: $SLURM_MEM_PER_NODE MB"
echo "Partition: $SLURM_JOB_PARTITION"
echo "=========================================="

# Set up Python environment
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv .venv
fi

source .venv/bin/activate

# Install dependencies
if [ -f "requirements_delftblue_py38.txt" ]; then
    echo "Installing DelftBlue Python 3.8 compatible dependencies..."
    pip install --upgrade pip
    pip install --no-cache-dir -r requirements_delftblue_py38.txt
elif [ -f "requirements.txt" ]; then
    echo "Installing HPC-optimized dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
elif [ -f "pyproject.toml" ]; then
    echo "Installing project dependencies..."
    pip install -e .
fi

# Set pipeline configuration for HPC environment
export WORKERS=$SLURM_CPUS_PER_TASK
export BATCH_SIZE=${BATCH_SIZE:-100}  # Larger batches for HPC
export ITERATIONS=${ITERATIONS:-}     # Infinite by default
export AZURE_INTERVAL=${AZURE_INTERVAL:-1000}  # Less frequent uploads for HPC

# Circuit generation parameters (can be overridden)
export MAX_QUBITS=${MAX_QUBITS:-5}
export MIN_QUBITS=${MIN_QUBITS:-1}
export MAX_DEPTH=${MAX_DEPTH:-2000}
export SIM_TIMEOUT=${SIM_TIMEOUT:-300}

echo "HPC Pipeline Configuration:"
echo "  Workers: $WORKERS"
echo "  Batch Size: $BATCH_SIZE"
echo "  Max Iterations: ${ITERATIONS:-infinite}"
echo "  Max Qubits: $MAX_QUBITS"
echo "  Azure Upload Interval: $AZURE_INTERVAL"
echo "=========================================="

# Use existing run_parallel.sh script with HPC optimizations
echo "Starting quantum circuit processing pipeline using existing scripts..."

# Make scripts executable
chmod +x scripts/*.sh

# Run the high-performance pipeline using your existing infrastructure
./scripts/run_parallel.sh \
    --workers $WORKERS \
    ${ITERATIONS:+--iterations $ITERATIONS} \
    --batch-size $BATCH_SIZE \
    --azure-interval $AZURE_INTERVAL

# Capture exit code
EXIT_CODE=$?

echo "=========================================="
echo "DelftBlue job completed with exit code: $EXIT_CODE"
echo "End Time: $(date)"
echo "=========================================="

# Optional: Archive results if requested
if [ "$ARCHIVE_RESULTS" = "true" ]; then
    echo "Archiving results..."
    tar -czf "results_${SLURM_JOB_ID}.tar.gz" circuits/ logs/ *.json
    echo "Results archived to: results_${SLURM_JOB_ID}.tar.gz"
fi

exit $EXIT_CODE