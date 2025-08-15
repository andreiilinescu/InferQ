#!/bin/bash
# InferQ Environment Activation Script

echo "🚀 Activating InferQ environment..."

# Add uv to PATH if needed
if [ -d "$HOME/.cargo/bin" ]; then
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Environment activated!"
else
    echo "❌ Virtual environment not found. Run ./setup_with_uv.sh first."
    exit 1
fi

echo ""
echo "Available commands:"
echo "  ./test-env-scripts/run_all_tests.sh  - Run all environment tests"
echo "  python3 main.py                      - Run single circuit pipeline"
echo "  python3 main_parallel.py             - Run parallel pipeline"
echo "  sbatch submit_delftblue.sh           - Submit to DelftBlue HPC"
echo "  ./monitor_slurm.sh                   - Monitor HPC jobs"
echo ""
echo "To deactivate: deactivate"
