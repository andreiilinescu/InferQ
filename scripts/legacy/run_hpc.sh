#!/bin/bash
# High-Performance Quantum Circuit Processing Pipeline
# Startup script for Intel Xeon E5-6248R 24C 3.0GHz, 185GB RAM

set -e  # Exit on any error

echo "🚀 Starting High-Performance Quantum Circuit Pipeline"
echo "=============================================="

# Check system resources
echo "System Information:"
echo "CPU cores: $(nproc)"
echo "Memory: $(free -h | grep '^Mem:' | awk '{print $2}')"
echo "Disk space: $(df -h . | tail -1 | awk '{print $4}') available"
echo ""

# Set optimal environment variables
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4
export NUMEXPR_NUM_THREADS=4
export PYTHONUNBUFFERED=1

# Create necessary directories
mkdir -p circuits_hpc
mkdir -p logs

# Check Azure connection
echo "Checking Azure connection..."
python3 -c "
try:
    from utils.azure_connection import AzureConnection
    conn = AzureConnection()
    print('✓ Azure connection successful')
except Exception as e:
    print(f'⚠️  Azure connection failed: {e}')
    print('⚠️  Pipeline will run in LOCAL ONLY mode')
"

# Set process priority for better performance
renice -n -5 $$ 2>/dev/null || echo "Note: Could not set process priority (requires sudo)"

# Default parameters (can be overridden) - optimized for remote storage
WORKERS=${WORKERS:-22}
ITERATIONS=${ITERATIONS:-}
BATCH_SIZE=${BATCH_SIZE:-50}
AZURE_INTERVAL=${AZURE_INTERVAL:-100}  # More frequent uploads

echo "Configuration:"
echo "Workers: $WORKERS"
echo "Batch size: $BATCH_SIZE"
echo "Azure upload interval: $AZURE_INTERVAL"
echo ""

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down pipeline..."
    # Kill any remaining Python processes
    pkill -f "main_parallel.py" 2>/dev/null || true
    echo "✓ Cleanup completed"
}

# Set up signal handlers
trap cleanup EXIT INT TERM

# Start the pipeline with optimal settings
echo "🏃 Starting pipeline execution..."
echo "Press Ctrl+C to stop gracefully"
echo ""

# Run with performance monitoring
if command -v htop >/dev/null 2>&1; then
    echo "💡 Tip: Run 'htop' in another terminal to monitor system resources"
fi

# Execute the main pipeline
python3 main_parallel.py \
    --workers "$WORKERS" \
    ${ITERATIONS:+--iterations "$ITERATIONS"} \
    --batch-size "$BATCH_SIZE" \
    --azure-interval "$AZURE_INTERVAL" \
    2>&1 | tee "logs/pipeline_$(date +%Y%m%d_%H%M%S).log"

echo ""
echo "✅ Pipeline execution completed"