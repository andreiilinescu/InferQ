import os
import sys
import argparse
import logging
import threading
import queue
from tqdm import tqdm
import qiskit.qpy

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.azure_connection import AzureConnection
from utils.table_storage import update_circuit_metadata_in_table
from utils.checkpoint_writer import AsyncCheckpointWriter
from simulators.simulate import QuantumSimulator, SimulationMethod
from config import PipelineConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("rerun_simulations.log")],
)
logger = logging.getLogger(__name__)
logging.getLogger("qiskit.passmanager.base_tasks").setLevel(logging.WARNING)
logging.getLogger("qiskit.compiler.transpiler").setLevel(logging.WARNING)


def rerun_simulations(
    circuits_dir,
    limit=None,
    verbose=False,
    mode="auto",
    checkpoint_file="rerun_checkpoint.txt",
    use_gpu=False,
):
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

    # Load checkpoint
    processed_hashes = set()
    if checkpoint_file and os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, "r") as f:
                processed_hashes = set(line.strip() for line in f if line.strip())
            logger.info(
                f"Loaded checkpoint. {len(processed_hashes)} circuits already processed."
            )
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")

    # Initialize Checkpoint Writer
    checkpoint_writer = None
    if checkpoint_file:
        checkpoint_writer = AsyncCheckpointWriter(checkpoint_file)

    # Initialize Simulator
    device = "GPU" if use_gpu else "CPU"
    simulator = QuantumSimulator(
        timeout_seconds=60, device=device
    )  # Set a reasonable timeout

    # Identify folders to process
    try:
        subdirs = [
            d
            for d in os.listdir(circuits_dir)
            if os.path.isdir(os.path.join(circuits_dir, d))
        ]
        subdirs.sort()
    except Exception as e:
        logger.error(f"Error listing directories in {circuits_dir}: {e}")
        return

    if not subdirs:
        logger.warning(f"No subdirectories found in {circuits_dir}")
        return

    logger.info(f"Found {len(subdirs)} folders to process.")

    count = 0

    for folder_name in tqdm(subdirs, desc="Processing folders"):
        if limit and count >= limit:
            break

        folder_path = os.path.join(circuits_dir, folder_name)
        try:
            files = [f for f in os.listdir(folder_path) if f.endswith(".qpy")]
            files.sort()
        except Exception as e:
            logger.error(f"Error listing files in {folder_path}: {e}")
            continue

        if not files:
            continue

        for filename in tqdm(files, desc=f"Processing {folder_name}", leave=False):
            if limit and count >= limit:
                break

            file_path = os.path.join(folder_path, filename)

            try:
                # Load circuit
                with open(file_path, "rb") as f:
                    circuits = qiskit.qpy.load(f)
                    qc = circuits[0] if isinstance(circuits, list) else circuits

                # Extract hash from filename (assuming hash.qpy)
                circuit_hash = os.path.splitext(filename)[0]

                if circuit_hash in processed_hashes:
                    continue

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
                            "automatic_method": actual_method,
                            "automatic_execution_time": result["execution_time"],
                            "automatic_memory_usage": result.get("memory_usage"),
                            "automatic_transpiled_depth": result.get(
                                "transpiled_circuit_depth"
                            ),
                            "automatic_transpiled_size": result.get(
                                "transpiled_circuit_size"
                            ),
                            "automatic_transpiled_qubits": result.get(
                                "transpiled_num_qubits"
                            ),
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
                                if result.get("method") == "automatic":
                                    updates["automatic_method"] = data["actual_method"]
                                
                                # Handle InfiniQuantumSim benchmark results if present in 'all' mode
                                if method_name == "infiniquantum" and "benchmark_results" in result:
                                    for bench_method, bench_data in result["benchmark_results"].items():
                                        if isinstance(bench_data, dict):
                                            if "memory_avg_mb" in bench_data:
                                                updates[f"rdbms_{bench_method}_memory_mb"] = bench_data["memory_avg_mb"]
                                            if "time_avg_s" in bench_data:
                                                updates[f"rdbms_{bench_method}_time_s"] = bench_data["time_avg_s"]

                elif mode == "rdbms":
                    logger.info(f"Simulating {circuit_hash} (InfiniQuantumSim)...")
                    # Run only InfiniQuantumSim
                    # Enable DuckDB by excluding it from oom list (skip list)
                    # We skip psql and sqlite by default as they might not be configured
                    result = simulator._run_simulation(
                        qc, 
                        SimulationMethod.INFINI_QUANTUM, 
                        oom=["psql", "eqc"]
                    )
                    
                    if result.get("success", False):
                        success_flag = True
                        updates["rdbms_execution_time"] = result.get("execution_time")
                        
                        if "benchmark_results" in result:
                            for bench_method, bench_data in result["benchmark_results"].items():
                                if isinstance(bench_data, dict):
                                    if "memory_avg_mb" in bench_data:
                                        updates[f"rdbms_{bench_method}_memory_mb"] = bench_data["memory_avg_mb"]
                                    if "time_avg_s" in bench_data:
                                        updates[f"rdbms_{bench_method}_time_s"] = bench_data["time_avg_s"]
                    else:
                        logger.warning(f"InfiniQuantumSim failed for {circuit_hash}: {result.get('error')}")

                if success_flag:
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
                        # Update checkpoint
                        if checkpoint_writer:
                            checkpoint_writer.add(circuit_hash)
                    else:
                        logger.warning(f"Failed to update table for {circuit_hash}")

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue

    if checkpoint_writer:
        checkpoint_writer.close()

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
        choices=["auto", "all", "rdbms"],
        default=None,
        help="Simulation mode: 'auto', 'all' or 'rdbms'.",
    )
    parser.add_argument(
        "--checkpoint-file",
        type=str,
        default="rerun_checkpoint.txt",
        help="File to store processed circuit hashes.",
    )
    parser.add_argument("--gpu", action="store_true", help="Enable GPU acceleration.")

    args = parser.parse_args()

    circuits_dir = args.circuits_dir
    limit = args.limit
    verbose = args.verbose
    mode = args.mode
    checkpoint_file = args.checkpoint_file
    use_gpu = args.gpu

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
                input("Enter simulation mode (auto/all/rdbms) [default: all]: ")
                .strip()
                .lower()
            )
            if user_input in ["auto", "all", "rdbms"]:
                mode = user_input
            else:
                mode = "all"
        except EOFError:
            mode = "all"
    
    # Set default checkpoint file for rdbms mode if not specified
    if mode == "rdbms" and checkpoint_file == "rerun_checkpoint.txt":
        checkpoint_file = "rerun_checkpoint_rdbms.txt"

    if not verbose:
        try:
            user_input = input("Enable verbose mode? (y/N): ").strip().lower()
            if user_input == "y":
                verbose = True
        except EOFError:
            pass

    if not use_gpu:
        try:
            user_input = input("Enable GPU acceleration? (y/N): ").strip().lower()
            if user_input == "y":
                use_gpu = True
        except EOFError:
            pass

    print(f"Circuits directory: {circuits_dir}")
    print(f"Limit: {limit if limit is not None else 'All'}")
    print(f"Mode: {mode}")
    print(f"Verbose: {verbose}")
    print(f"Checkpoint File: {checkpoint_file}")
    print(f"GPU Enabled: {use_gpu}")

    rerun_simulations(circuits_dir, limit, verbose, mode, checkpoint_file, use_gpu)
