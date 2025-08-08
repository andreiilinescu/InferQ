#!/bin/bash
# High-Performance Pipeline Runner
# Full production parallel pipeline for continuous operation

set -e  # Exit on any error

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Source utility scripts
source "$SCRIPT_DIR/system_info.sh"
source "$SCRIPT_DIR/azure_check.sh"
source "$SCRIPT_DIR/pipeline_monitor.sh"

# Configuration
SCRIPT_NAME="main_parallel_new.py"
LOG_DIR="logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/parallel_pipeline_${TIMESTAMP}.log"
PID_FILE="${LOG_DIR}/pipeline.pid"

# HPC parameters (can be overridden via environment variables)
WORKERS=${WORKERS:-}  # Auto-detect if not set (typically CPU-2)
ITERATIONS=${ITERATIONS:-}  # Infinite by default
BATCH_SIZE=${BATCH_SIZE:-200}  # Large batches for HPC
AZURE_INTERVAL=${AZURE_INTERVAL:-500}  # Frequent uploads for HPC

# Create necessary directories
mkdir -p "$LOG_DIR"
mkdir -p circuits

# Function to handle cleanup on exit
cleanup() {
    cleanup_pipeline "$PID_FILE" "$SCRIPT_NAME"
}

# Set up signal handlers
trap cleanup EXIT INT TERM

# Check if Python script exists
if [ ! -f "$PROJECT_DIR/$SCRIPT_NAME" ]; then
    print_error "Error: $SCRIPT_NAME not found in project directory"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "Warning: No virtual environment detected. Make sure required packages are installed."
fi

print_success "🚀 Starting High-Performance Pipeline (Full Production Mode)"
print_status "=============================================="

# Show system information and setup environment
setup_environment
show_system_info

# Auto-detect workers if not set
WORKERS=$(get_optimal_workers "$WORKERS")

# Check Azure connection
check_azure_connection

# Set process priority for better performance (if possible)
optimize_process

print_status "Configuration:"
echo "  Workers: $WORKERS"
echo "  Batch size: $BATCH_SIZE"
echo "  Azure upload interval: $AZURE_INTERVAL"
echo "  Log file: $LOG_FILE"
echo "  PID file: $PID_FILE"
echo ""

# Show performance monitoring tip
show_monitoring_tip

print_success "🏃 Starting pipeline execution..."
print_status "Press Ctrl+C to stop gracefully"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Start the pipeline with optimal settings and logging
python3 "$SCRIPT_NAME" \
    --workers "$WORKERS" \
    ${ITERATIONS:+--iterations "$ITERATIONS"} \
    --batch-size "$BATCH_SIZE" \
    --azure-interval "$AZURE_INTERVAL" \
    2>&1 | tee "$LOG_FILE" &

PIPELINE_PID=$!

# Save PID for monitoring
echo $PIPELINE_PID > "$PID_FILE"

# Monitor the pipeline
monitor_pipeline $PIPELINE_PID "$LOG_FILE" "$PID_FILE"
EXIT_CODE=$?

# Show results
show_results $EXIT_CODE "$LOG_FILE"

exit $EXIT_CODE