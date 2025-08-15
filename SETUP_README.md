# InferQ Environment Setup with UV

Fast and reliable environment setup for the quantum circuit processing pipeline using UV package manager.

## Quick Start

```bash
# 1. Run the setup script
./setup_with_uv.sh

# 2. Activate the environment
./activate_env.sh

# 3. Run tests
./test-env-scripts/run_all_tests.sh

# 4. Submit to DelftBlue (if on HPC)
sbatch submit_delftblue.sh
```

## What the Setup Script Does

### 🔍 **System Detection**
- Detects operating system (Linux/macOS)
- Identifies DelftBlue HPC environment
- Checks Python version (requires 3.8+)
- Loads appropriate HPC modules

### 📦 **UV Installation**
- Installs UV package manager using official installer
- Adds UV to PATH automatically
- Verifies installation

### 🐍 **Environment Creation**
- Creates `.venv` virtual environment with UV
- Handles existing environments gracefully
- Sets up activation scripts

### 📚 **Dependency Installation**
- Prioritizes `requirements_delftblue_py38.txt` for Python 3.8 compatibility
- Falls back to other requirements files or pyproject.toml
- Installs core quantum computing packages if no requirements found

### ✅ **Verification**
- Tests critical package imports
- Verifies quantum computing functionality
- Reports any issues

### 🛠️ **Helper Scripts**
- Creates `activate_env.sh` for easy environment activation
- Creates `submit_quick_test.sh` for HPC testing (DelftBlue only)

## Requirements Files Priority

1. **`requirements_delftblue_py38.txt`** - Python 3.8 compatible (DelftBlue)
2. **`requirements_hpc.txt`** - General HPC requirements
3. **`requirements.txt`** - Standard requirements
4. **`pyproject.toml`** - Project dependencies
5. **Core packages** - Minimal quantum computing stack

## DelftBlue HPC Usage

### On Login Node
```bash
# Load Python module first
module load python/3.8.12

# Run setup
./setup_with_uv.sh

# Activate environment
./activate_env.sh

# Submit jobs
sbatch submit_delftblue.sh          # Full production
sbatch submit_quick_test.sh         # Quick test (30 min)
```

### Monitoring Jobs
```bash
# Check job status
./monitor_slurm.sh jobs

# View logs
./monitor_slurm.sh logs

# Watch specific job
./monitor_slurm.sh watch <job_id>
```

## Local Development

### macOS
```bash
# Install UV (if not already installed)
brew install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run setup
./setup_with_uv.sh
```

### Linux
```bash
# UV will be installed automatically
./setup_with_uv.sh
```

## Troubleshooting

### UV Installation Issues
```bash
# Manual UV installation
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"
```

### Python Version Issues
```bash
# On DelftBlue
module load python/3.8.12

# Check version
python3 --version
```

### Package Installation Issues
```bash
# Activate environment first
./activate_env.sh

# Install specific package
uv pip install package_name

# Reinstall all dependencies
uv pip install -r requirements_delftblue_py38.txt --force-reinstall
```

### Virtual Environment Issues
```bash
# Remove and recreate
rm -rf .venv
./setup_with_uv.sh
```

## Advantages of UV

- **Fast**: 10-100x faster than pip
- **Reliable**: Better dependency resolution
- **Compatible**: Drop-in replacement for pip
- **Cross-platform**: Works on Linux, macOS, Windows
- **HPC-friendly**: No compilation needed, single binary

## Environment Structure

After setup, your environment will have:

```
InferQ/
├── .venv/                          # Virtual environment
├── activate_env.sh                 # Environment activation
├── setup_with_uv.sh               # This setup script
├── submit_delftblue.sh            # HPC job submission
├── submit_quick_test.sh           # Quick HPC test (created on HPC)
├── requirements_delftblue_py38.txt # Python 3.8 requirements
├── test-env-scripts/              # Environment tests
│   ├── run_all_tests.sh
│   ├── 01_test_python.py
│   ├── 02_test_packages.py
│   ├── 03_test_azure.py
│   └── ...
└── main.py                        # Quantum pipeline
```

## Next Steps After Setup

1. **Test Environment**: `./test-env-scripts/run_all_tests.sh`
2. **Configure Azure**: Set environment variables in `.env`
3. **Test Pipeline**: `python3 main.py`
4. **Submit to HPC**: `sbatch submit_delftblue.sh`
5. **Monitor Progress**: `./monitor_slurm.sh`

## Support

- **DelftBlue Documentation**: https://doc.dhpc.tudelft.nl/delftblue/
- **UV Documentation**: https://docs.astral.sh/uv/
- **Project Issues**: Check test outputs and logs