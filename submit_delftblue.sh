#!/bin/bash
#SBATCH --job-name=inferq_quantum
#SBATCH --partition=compute
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem-per-cpu=3690MB
#SBATCH --account=research-eemcs-qce

# Output and error files
#SBATCH --output=logs/slurm_%j.out
#SBATCH --error=logs/slurm_%j.err


# Load required modules for DelftBlue
module load 2023r1
module load python/3.12.6

# Change to the correct directory (current directory should be the project root)
echo "Current directory: $(pwd)"
echo "Directory contents:"
ls -la

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


# Set pipeline configuration for HPC environment
export WORKERS=$SLURM_CPUS_PER_TASK
export BATCH_SIZE=${BATCH_SIZE:-100}  # Larger batches for HPC
export ITERATIONS=${ITERATIONS:-}     # Infinite by default
export AZURE_INTERVAL=${AZURE_INTERVAL:-1000}  # Less frequent uploads for HPC


echo "HPC Pipeline Configuration:"
echo "  Workers: $WORKERS"
echo "  Batch Size: $BATCH_SIZE"
echo "  Max Iterations: ${ITERATIONS:-infinite}"
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