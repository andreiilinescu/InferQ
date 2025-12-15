import os
import sys
import argparse
import logging
from tqdm import tqdm
import qiskit.qpy

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.azure_connection import AzureConnection
from utils.table_storage import update_circuit_metadata_in_table
from simulators.simulate import QuantumSimulator
from config import PipelineConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("rerun_simulations.log")],
)
logger = logging.getLogger(__name__)


def rerun_simulations(circuits_dir, limit=None, verbose=False, mode="auto"):
    """
    Reruns simulations for circuits in the specified directory and updates Azure Table.
    """
    if not os.path.exists(circuits_dir):
        logger.error(f"Circuits directory not found: {circuits_dir}")
        return

    # Initialize Azure connection
    try:
        azure_conn = AzureConnection()
        table_client = azure_conn.circuits_table_client
        logger.info("Connected to Azure Table Storage.")
    except Exception as e:
        logger.error(f"Failed to connect to Azure: {e}")
        return

    # Initialize Simulator
    simulator = QuantumSimulator(timeout_seconds=60)  # Set a reasonable timeout

    # Find QPY files
    # We might have subdirectories (e.g. 00/hash.qpy)
    qpy_files = []
    for root, dirs, files in os.walk(circuits_dir):
        for file in files:
            if file.endswith(".qpy"):
                qpy_files.append(os.path.join(root, file))

    if not qpy_files:
        logger.warning(f"No QPY files found in {circuits_dir}")
        return

    logger.info(f"Found {len(qpy_files)} QPY files.")

    count = 0

    for file_path in tqdm(qpy_files, desc="Processing circuits"):
        if limit and count >= limit:
            break

        try:
            # Load circuit
            with open(file_path, "rb") as f:
                circuits = qiskit.qpy.load(f)
                qc = circuits[0] if isinstance(circuits, list) else circuits

            # Extract hash from filename (assuming hash.qpy)
            filename = os.path.basename(file_path)
            circuit_hash = os.path.splitext(filename)[0]

            updates = {}
            success_flag = False

            if mode == "auto":
                # Run auto simulation
                logger.info(f"Simulating {circuit_hash} (auto)...")
                result = simulator.simulate_auto(qc)

                if result["success"]:
                    success_flag = True
                    # Prepare updates
                    data = result.get("data", {})
                    actual_method = data.get("actual_method", result["method"])

                    updates = {
                        "simulation_method": actual_method,
                        "execution_time": result["execution_time"],
                        "memory_usage": result.get("memory_usage"),
                        "transpiled_depth": result.get("transpiled_circuit_depth"),
                        "transpiled_size": result.get("transpiled_circuit_size"),
                        "transpiled_qubits": result.get("transpiled_num_qubits"),
                    }
                else:
                    logger.warning(
                        f"Simulation failed for {circuit_hash}: {result.get('error')}"
                    )

            elif mode == "all":
                # Run all simulations
                logger.info(f"Simulating {circuit_hash} (all methods)...")
                results = simulator.simulate_all_methods(qc)

                # Check if any method succeeded
                if any(r.get("success", False) for r in results.values()):
                    success_flag = True

                    for method_name, result in results.items():
                        if result.get("success", False):
                            # Add method-specific columns
                            prefix = method_name
                            updates[f"{prefix}_execution_time"] = result.get(
                                "execution_time"
                            )
                            updates[f"{prefix}_memory_usage"] = result.get(
                                "memory_usage"
                            )
                            updates[f"{prefix}_transpiled_depth"] = result.get(
                                "transpiled_circuit_depth"
                            )
                            updates[f"{prefix}_transpiled_size"] = result.get(
                                "transpiled_circuit_size"
                            )
                            updates[f"{prefix}_gate_counts"] = result.get(
                                "transpiled_gate_counts"
                            )

                            # Add extra data if available (e.g. entropy for statevector)
                            data = result.get("data", {})
                            if "entropy" in data:
                                updates[f"{prefix}_entropy"] = data["entropy"]
                            if "sparsity" in data:
                                updates[f"{prefix}_sparsity"] = data["sparsity"]
                else:
                    logger.warning(f"All simulations failed for {circuit_hash}")

            if success_flag and updates:
                if verbose:
                    logger.info(f"Updates for {circuit_hash}: {updates}")

                # Update Azure Table
                success = update_circuit_metadata_in_table(
                    table_client, circuit_hash, updates
                )
                if success:
                    count += 1
                else:
                    logger.warning(f"Failed to update table for {circuit_hash}")

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            continue

    logger.info(f"Rerun complete. Total circuits updated: {count}")


if __name__ == "__main__":
    config = PipelineConfig()

    parser = argparse.ArgumentParser(
        description="Rerun simulations and update Azure Table."
    )
    parser.add_argument(
        "--circuits-dir",
        type=str,
        default=None,
        help="Directory containing circuits.",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Maximum number of circuits to process."
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["auto", "all"],
        default=None,
        help="Simulation mode: 'auto' or 'all'.",
    )

    args = parser.parse_args()

    circuits_dir = args.circuits_dir
    limit = args.limit
    verbose = args.verbose
    mode = args.mode

    # Interactive prompts if arguments are not provided
    if circuits_dir is None:
        default_dir = str(config.circuits_dir)
        try:
            user_input = input(
                f"Enter circuits directory [default: {default_dir}]: "
            ).strip()
            circuits_dir = user_input if user_input else default_dir
        except EOFError:
            circuits_dir = default_dir

    if limit is None:
        try:
            user_input = input(
                "Enter number of circuits to process (or press Enter for all): "
            ).strip()
            if user_input:
                try:
                    limit = int(user_input)
                except ValueError:
                    print("Invalid number. Defaulting to all.")
                    limit = None
            else:
                limit = None
        except EOFError:
            limit = None

    if mode is None:
        try:
            user_input = (
                input("Enter simulation mode (auto/all) [default: auto]: ")
                .strip()
                .lower()
            )
            if user_input in ["auto", "all"]:
                mode = user_input
            else:
                mode = "auto"
        except EOFError:
            mode = "auto"

    if not verbose:
        try:
            user_input = input("Enable verbose mode? (y/N): ").strip().lower()
            if user_input == "y":
                verbose = True
        except EOFError:
            pass

    print(f"Circuits directory: {circuits_dir}")
    print(f"Limit: {limit if limit is not None else 'All'}")
    print(f"Mode: {mode}")
    print(f"Verbose: {verbose}")

    rerun_simulations(circuits_dir, limit, verbose, mode)
