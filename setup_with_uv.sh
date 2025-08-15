#!/bin/bash
# InferQ Environment Setup with UV
# Fast Python package manager for quantum circuit processing pipeline

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "${BLUE}🔧 $1${NC}"
    echo "$(printf '=%.0s' $(seq 1 $((${#1} + 3))))"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "   $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect system
detect_system() {
    print_header "System Detection"
    
    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        print_info "Operating System: Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        print_info "Operating System: macOS"
    else
        OS="unknown"
        print_warning "Unknown operating system: $OSTYPE"
    fi
    
    # Check if on DelftBlue
    if [[ $(hostname) == *"delftblue"* ]] || [[ $(hostname) == *"login"* ]]; then
        ON_HPC=true
        print_success "Running on DelftBlue HPC system"
        
        # Check if in Slurm job
        if [ -n "$SLURM_JOB_ID" ]; then
            print_info "In Slurm job: $SLURM_JOB_ID"
            print_info "CPUs: $SLURM_CPUS_PER_TASK"
            print_info "Memory: $SLURM_MEM_PER_NODE MB"
        else
            print_info "On login node"
        fi
    else
        ON_HPC=false
        print_info "Running on local system"
    fi
    
    # Check Python version
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_info "Python version: $PYTHON_VERSION"
        
        # Check if Python 3.8+
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            print_success "Python version is compatible (3.8+)"
            PYTHON_OK=true
        else
            print_error "Python version too old (need 3.8+, got $PYTHON_VERSION)"
            PYTHON_OK=false
        fi
    else
        print_error "Python3 not found"
        PYTHON_OK=false
    fi
    
    echo ""
}

# Function to load HPC modules if needed
load_hpc_modules() {
    if [ "$ON_HPC" = true ]; then
        print_header "Loading HPC Modules"
        
        # Load required modules for DelftBlue
        if command_exists module; then
            print_info "Loading Python module..."
            module purge 2>/dev/null || true
            module load 2023r1 2>/dev/null || true
            module load python/3.8.12 2>/dev/null || print_warning "Could not load python/3.8.12"
            
            print_info "Loaded modules:"
            module list 2>&1 | grep -E "(python|2023r1)" || print_warning "No modules loaded"
        else
            print_warning "Module system not available"
        fi
        echo ""
    fi
}

# Function to install uv
install_uv() {
    print_header "UV Package Manager Installation"
    
    # Check if uv is already installed
    if command_exists uv; then
        UV_VERSION=$(uv --version 2>/dev/null || echo "unknown")
        print_success "UV already installed: $UV_VERSION"
        return 0
    fi
    
    print_info "Installing uv package manager..."
    
    # Install uv using the official installer
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        print_success "UV installer completed"
        
        # Add uv to PATH for current session
        export PATH="$HOME/.cargo/bin:$PATH"
        
        # Verify installation
        if command_exists uv; then
            UV_VERSION=$(uv --version 2>/dev/null || echo "unknown")
            print_success "UV successfully installed: $UV_VERSION"
            return 0
        else
            print_error "UV installation failed - command not found after install"
            return 1
        fi
    else
        print_error "Failed to install uv"
        return 1
    fi
}

# Function to create virtual environment
create_venv() {
    print_header "Virtual Environment Setup"
    
    # Check if .venv already exists
    if [ -d ".venv" ]; then
        print_warning "Virtual environment already exists"
        read -p "Remove existing environment? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Removing existing virtual environment..."
            rm -rf .venv
            print_success "Removed existing environment"
        else
            print_info "Using existing virtual environment"
            return 0
        fi
    fi
    
    # Create virtual environment with uv
    print_info "Creating virtual environment with uv..."
    if uv venv .venv; then
        print_success "Virtual environment created"
        
        # Verify activation script exists
        if [ -f ".venv/bin/activate" ]; then
            print_success "Activation script ready"
            return 0
        else
            print_error "Activation script not found"
            return 1
        fi
    else
        print_error "Failed to create virtual environment"
        return 1
    fi
}

# Function to install dependencies
install_dependencies() {
    print_header "Installing Dependencies"
    
    # Activate virtual environment
    print_info "Activating virtual environment..."
    source .venv/bin/activate
    
    # Determine which requirements file to use
    if [ -f "requirements_delftblue_py38.txt" ]; then
        REQUIREMENTS_FILE="requirements_delftblue_py38.txt"
        print_info "Using DelftBlue Python 3.8 requirements"
    elif [ -f "requirements_hpc.txt" ]; then
        REQUIREMENTS_FILE="requirements_hpc.txt"
        print_info "Using HPC requirements"
    elif [ -f "requirements.txt" ]; then
        REQUIREMENTS_FILE="requirements.txt"
        print_info "Using standard requirements"
    else
        REQUIREMENTS_FILE=""
        print_warning "No requirements file found"
    fi
    
    # Install dependencies
    if [ -n "$REQUIREMENTS_FILE" ]; then
        print_info "Installing packages from $REQUIREMENTS_FILE..."
        if uv pip install -r "$REQUIREMENTS_FILE"; then
            print_success "Dependencies installed successfully"
        else
            print_error "Failed to install some dependencies"
            return 1
        fi
    elif [ -f "pyproject.toml" ]; then
        print_info "Installing project from pyproject.toml..."
        if uv pip install -e .; then
            print_success "Project installed successfully"
        else
            print_error "Failed to install project"
            return 1
        fi
    else
        print_info "Installing minimal core dependencies..."
        
        # Core packages for quantum computing
        CORE_PACKAGES=(
            "qiskit>=0.45.0,<1.0.0"
            "qiskit-aer>=0.13.0,<0.15.0"
            "numpy>=1.20.0,<2.0.0"
            "scipy>=1.7.0,<1.12.0"
            "pandas>=1.3.0,<2.0.0"
            "networkx>=2.6,<3.5.0"
            "psutil>=5.8.0"
            "tqdm>=4.60.0"
            "python-dotenv>=0.19.0"
        )
        
        for package in "${CORE_PACKAGES[@]}"; do
            package_name=$(echo "$package" | cut -d'>' -f1 | cut -d'=' -f1)
            print_info "Installing $package_name..."
            if ! uv pip install "$package"; then
                print_warning "Failed to install $package"
            fi
        done
        
        print_success "Core dependencies installed"
    fi
    
    echo ""
}

# Function to verify installation
verify_installation() {
    print_header "Installation Verification"
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Test critical imports
    CRITICAL_PACKAGES=("qiskit" "qiskit_aer" "numpy" "scipy" "pandas" "networkx" "psutil" "tqdm")
    FAILED_IMPORTS=()
    
    for package in "${CRITICAL_PACKAGES[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            print_success "$package imported successfully"
        else
            print_error "$package import failed"
            FAILED_IMPORTS+=("$package")
        fi
    done
    
    if [ ${#FAILED_IMPORTS[@]} -eq 0 ]; then
        print_success "All critical packages verified"
        return 0
    else
        print_error "Failed imports: ${FAILED_IMPORTS[*]}"
        return 1
    fi
}

# Function to create activation script
create_activation_script() {
    print_header "Creating Activation Script"
    
    cat > activate_env.sh << 'EOF'
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
EOF

    chmod +x activate_env.sh
    print_success "Created activation script: activate_env.sh"
}

# Function to create DelftBlue submission helper
create_delftblue_helper() {
    if [ "$ON_HPC" = true ]; then
        print_header "Creating DelftBlue Helper Scripts"
        
        # Create quick job submission script
        cat > submit_quick_test.sh << 'EOF'
#!/bin/bash
#SBATCH --job-name=inferq_test
#SBATCH --partition=compute
#SBATCH --time=00:30:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --account=research-eemcs-qce
#SBATCH --output=logs/test_%j.out
#SBATCH --error=logs/test_%j.err

echo "Quick InferQ test job starting..."
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"

# Load modules
module purge
module load 2023r1
module load python/3.8.12

# Activate environment
source .venv/bin/activate

# Run tests
./test-env-scripts/run_all_tests.sh --quick

echo "Test job completed"
EOF

        chmod +x submit_quick_test.sh
        print_success "Created quick test submission: submit_quick_test.sh"
    fi
}

# Function to show final instructions
show_final_instructions() {
    print_header "Setup Complete!"
    
    print_success "InferQ environment successfully set up with UV!"
    echo ""
    
    echo "Next steps:"
    echo "1. Activate environment:"
    echo "   ./activate_env.sh"
    echo ""
    echo "2. Run environment tests:"
    echo "   ./test-env-scripts/run_all_tests.sh"
    echo ""
    echo "3. Test quantum pipeline:"
    echo "   python3 main.py"
    echo ""
    
    if [ "$ON_HPC" = true ]; then
        echo "4. Submit to DelftBlue HPC:"
        echo "   sbatch submit_delftblue.sh          # Full production job"
        echo "   sbatch submit_quick_test.sh         # Quick test job"
        echo ""
        echo "5. Monitor jobs:"
        echo "   ./monitor_slurm.sh jobs"
        echo "   ./monitor_slurm.sh logs"
        echo ""
        
        print_info "HPC Tips:"
        echo "  - Check queue: squeue -u \$USER"
        echo "  - Check resources: sinfo"
        echo "  - Cancel job: scancel <job_id>"
    else
        echo "4. For HPC deployment:"
        echo "   scp -r . username@login.delftblue.tudelft.nl:~/inferq/"
        echo "   ssh username@login.delftblue.tudelft.nl"
        echo "   cd inferq && ./setup_with_uv.sh"
    fi
    
    echo ""
    print_success "Environment ready for quantum circuit processing!"
}

# Main execution
main() {
    echo "🚀 InferQ Environment Setup with UV"
    echo "===================================="
    echo "Fast Python package manager for quantum circuit processing"
    echo ""
    
    # Detect system and requirements
    detect_system
    
    if [ "$PYTHON_OK" != true ]; then
        print_error "Python requirements not met. Please install Python 3.8+ first."
        exit 1
    fi
    
    # Load HPC modules if needed
    load_hpc_modules
    
    # Install uv
    if ! install_uv; then
        print_error "Failed to install UV package manager"
        exit 1
    fi
    
    # Create virtual environment
    if ! create_venv; then
        print_error "Failed to create virtual environment"
        exit 1
    fi
    
    # Install dependencies
    if ! install_dependencies; then
        print_error "Failed to install dependencies"
        exit 1
    fi
    
    # Verify installation
    if ! verify_installation; then
        print_warning "Some packages failed verification, but continuing..."
    fi
    
    # Create helper scripts
    create_activation_script
    create_delftblue_helper
    
    # Show final instructions
    show_final_instructions
    
    return 0
}

# Run main function
main "$@"