#!/bin/bash
# Light Pipeline Runner
# Runs with conservative settings for testing or resource-limited environments

set -e  # Exit on any error

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Source utility scripts
source "$SCRIPT_DIR/system_info.sh"
source "$SCRIPT_DIR/azure_check.sh"

# Configuration
SCRIPT_NAME="main_parallel_new.py"
LOG_DIR="logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/light_pipeline_${TIMESTAMP}.log"

# Light parameters (can be overridden via environment variables)
WORKERS=${WORKERS:-4}  # Conservative worker count
ITERATIONS=${ITERATIONS:-}  # Can run indefinitely but with lighter load
BATCH_SIZE=${BATCH_SIZE:-50}  # Smaller batches
AZURE_INTERVAL=${AZURE_INTERVAL:-2000}  # Less frequent uploads

# Create necessary directories
mkdir -p "$LOG_DIR"
mkdir -p circuits

# Function to handle cleanup on exit
cleanup() {
    print_success "✓ Light pipeline completed"
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

print_success "🚀 Starting Light Pipeline (Conservative Mode)"
print_status "=============================================="

# Show system information and setup environment
setup_environment
show_system_info

# Check Azure connection
check_azure_connection

print_status "Light Pipeline Configuration:"
echo "  Workers: $WORKERS (conservative)"
echo "  Iterations: $ITERATIONS (can run indefinitely)"
echo "  Batch size: $BATCH_SIZE (moderate)"
echo "  Azure upload interval: $AZURE_INTERVAL (less frequent)"
echo "  Log file: $LOG_FILE"
echo ""

print_success "🏃 Starting light pipeline execution..."
print_status "Press Ctrl+C to stop gracefully"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Execute the light pipeline
python3 "$SCRIPT_NAME" \
    --workers "$WORKERS" \
    ${ITERATIONS:+--iterations "$ITERATIONS"} \
    --batch-size "$BATCH_SIZE" \
    --azure-interval "$AZURE_INTERVAL" \
    2>&1 | tee "$LOG_FILE"

EXIT_CODE=$?

# Report results
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    print_success "✅ Light pipeline completed successfully!"
else
    print_error "❌ Light pipeline failed with exit code: $EXIT_CODE"
fi

print_status "Log available at: $LOG_FILE"

exit $EXIT_CODE