#!/bin/bash

# Force Cleanup and Restart Script
# This script aggressively cleans up all stuck processes and restarts with minimal settings

echo "🛑 FORCE CLEANUP: Stopping ALL pipeline processes..."

# Kill all Python processes related to the pipeline
echo "Killing main pipeline processes..."
pkill -9 -f "main_parallel.py"
pkill -9 -f "run_parallel.sh"

# Kill all multiprocessing worker processes
echo "Killing stuck multiprocessing workers..."
pkill -9 -f "multiprocessing.spawn"
pkill -9 -f "multiprocessing.resource_tracker"

# Kill any remaining Python processes that might be stuck on simulations
echo "Killing simulation processes..."
pkill -9 -f "qiskit"
pkill -9 -f "aer"

# Wait for processes to die
sleep 5

# Double-check and force kill any remaining processes
REMAINING_PROCESSES=$(pgrep -f "multiprocessing.*InferQ")
if [ ! -z "$REMAINING_PROCESSES" ]; then
    echo "Force killing remaining processes: $REMAINING_PROCESSES"
    kill -9 $REMAINING_PROCESSES
fi

# Clean up any leftover PID files
rm -f logs/pipeline.pid
rm -f logs/*.pid

echo "✓ All processes cleaned up"

# Clear Python cache to prevent issues
echo "Clearing Python cache..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Wait for system to stabilize
sleep 10

echo "🚀 Starting MINIMAL pipeline configuration..."

# Set very conservative environment variables for minimal resource usage
export MAX_QUBITS=15           # Very small circuits only
export MAX_DEPTH=50            # Very shallow circuits
export MAX_CIRCUIT_SIZE=500    # Very few gates
export SIM_TIMEOUT=15          # Very short timeout
export WORKERS=3               # Only 3 workers
export BATCH_SIZE=3            # Match number of workers so all get used
export MAX_GENERATORS=2        # Minimal generators
export STOPPING_PROB=0.7       # High stopping probability

echo "Configuration:"
echo "  Max qubits: $MAX_QUBITS"
echo "  Max depth: $MAX_DEPTH"
echo "  Max circuit size: $MAX_CIRCUIT_SIZE"
echo "  Simulation timeout: $SIM_TIMEOUT seconds"
echo "  Workers: $WORKERS"
echo "  Batch size: $BATCH_SIZE"

# Start the pipeline with minimal settings
./scripts/run_parallel.sh

echo "✅ Pipeline restarted with minimal configuration"