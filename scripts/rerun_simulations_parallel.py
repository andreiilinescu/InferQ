import os
import sys
import argparse
import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import qiskit.qpy
import time

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
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("rerun_simulations_parallel.log"),
    ],
)
logging.getLogger("qiskit.passmanager.base_tasks").setLevel(logging.WARNING)
logging.getLogger("qiskit.compiler.transpiler").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def process_circuit(file_path, mode):
    """
    Worker function to process a single circuit.
    """
    try:
        # Initialize Simulator inside worker to ensure fresh state and avoid pickling issues
        simulator = QuantumSimulator(timeout_seconds=60)

        # Load circuit
        with open(file_path, "rb") as f:
            circuits = qiskit.qpy.load(f)
            qc = circuits[0] if isinstance(circuits, list) else circuits

        # Extract hash from filename
        filename = os.path.basename(file_path)
        circuit_hash = os.path.splitext(filename)[0]

        updates = {}
        success = False
        error_msg = None

        if mode == "auto":
            result = simulator.simulate_auto(qc)
            if result["success"]:
                success = True
                data = result.get("data", {})
                actual_method = data.get("actual_method", result["method"])
                updates = {
                    "automatic_method": actual_method,
                    "automatic_execution_time": result["execution_time"],
                    "automatic_memory_usage": result.get("memory_usage"),
                    "automatic_transpiled_depth": result.get(
                        "transpiled_circuit_depth"
                    ),
                    "automatic_transpiled_size": result.get("transpiled_circuit_size"),
                    "automatic_transpiled_qubits": result.get("transpiled_num_qubits"),
                }
            else:
                error_msg = result.get("error")

        elif mode == "all":
            results = simulator.simulate_all_methods(qc)
            if any(r.get("success", False) for r in results.values()):
                success = True
                for method_name, result in results.items():
                    if result.get("success", False):
                        prefix = method_name
                        updates[f"{prefix}_execution_time"] = result.get(
                            "execution_time"
                        )
                        updates[f"{prefix}_memory_usage"] = result.get("memory_usage")
                        updates[f"{prefix}_transpiled_depth"] = result.get(
                            "transpiled_circuit_depth"
                        )
                        updates[f"{prefix}_transpiled_size"] = result.get(
                            "transpiled_circuit_size"
                        )
                        updates[f"{prefix}_gate_counts"] = result.get(
                            "transpiled_gate_counts"
                        )

                        data = result.get("data", {})
                        if "entropy" in data:
                            updates[f"{prefix}_entropy"] = data["entropy"]
                        if "sparsity" in data:
                            updates[f"{prefix}_sparsity"] = data["sparsity"]
                        if result.get("method") == "automatic":
                            updates["automatic_method"] = data["actual_method"]
            else:
                error_msg = "All simulations failed"

        return {
            "hash": circuit_hash,
            "success": success,
            "updates": updates,
            "error": error_msg,
            "file_path": file_path,
        }

    except Exception as e:
        return {
            "hash": os.path.splitext(os.path.basename(file_path))[0],
            "success": False,
            "updates": {},
            "error": str(e),
            "file_path": file_path,
        }


def rerun_simulations_parallel(
    circuits_dir,
    limit=None,
    verbose=False,
    mode="auto",
    checkpoint_file="rerun_checkpoint.txt",
    num_workers=None,
):
    """
    Reruns simulations for circuits in parallel and updates Azure Table.
    """
    if not os.path.exists(circuits_dir):
        logger.error(f"Circuits directory not found: {circuits_dir}")
        return

    # Initialize Azure connection (in main process)
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

    # Find QPY files
    qpy_files = []
    for root, dirs, files in os.walk(circuits_dir):
        for file in files:
            if file.endswith(".qpy"):
                qpy_files.append(os.path.join(root, file))

    if not qpy_files:
        logger.warning(f"No QPY files found in {circuits_dir}")
        return

    logger.info(f"Found {len(qpy_files)} QPY files.")

    # Filter out processed files
    files_to_process = []
    for file_path in qpy_files:
        filename = os.path.basename(file_path)
        circuit_hash = os.path.splitext(filename)[0]
        if circuit_hash not in processed_hashes:
            files_to_process.append(file_path)

    if limit:
        files_to_process = files_to_process[:limit]

    logger.info(f"Processing {len(files_to_process)} circuits after filtering.")

    if not files_to_process:
        logger.info("No new circuits to process.")
        return

    # Determine number of workers
    if num_workers is None:
        num_workers = max(
            1, mp.cpu_count() - 2
        )  # Leave some cores for system/main process

    logger.info(f"Starting parallel execution with {num_workers} workers.")

    # Process in parallel
    success_count = 0
    fail_count = 0

    executor = ProcessPoolExecutor(max_workers=num_workers)
    try:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_circuit, file_path, mode): file_path
            for file_path in files_to_process
        }

        # Process results as they complete
        with tqdm(total=len(files_to_process), desc="Processing circuits") as pbar:
            for future in as_completed(future_to_file):
                result = future.result()
                circuit_hash = result["hash"]

                if result["success"]:
                    updates = result["updates"]
                    if verbose:
                        logger.info(f"Updates for {circuit_hash}: {updates}")

                    # Update Azure Table (in main process)
                    try:
                        success = update_circuit_metadata_in_table(
                            table_client, circuit_hash, updates
                        )
                        if success:
                            success_count += 1
                            # Update checkpoint
                            if checkpoint_file:
                                with open(checkpoint_file, "a") as f:
                                    f.write(f"{circuit_hash}\n")
                        else:
                            logger.warning(f"Failed to update table for {circuit_hash}")
                            fail_count += 1
                    except Exception as e:
                        logger.error(f"Error updating table for {circuit_hash}: {e}")
                        fail_count += 1
                else:
                    logger.warning(
                        f"Simulation failed for {circuit_hash}: {result.get('error')}"
                    )
                    fail_count += 1

                pbar.update(1)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Shutting down workers...")
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    finally:
        executor.shutdown(wait=True)

    logger.info(f"Rerun complete. Successful: {success_count}, Failed: {fail_count}")


if __name__ == "__main__":
    config = PipelineConfig()

    parser = argparse.ArgumentParser(
        description="Rerun simulations and update Azure Table in PARALLEL."
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
    parser.add_argument(
        "--checkpoint-file",
        type=str,
        default="rerun_checkpoint.txt",
        help="File to store processed circuit hashes.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of worker processes (default: CPU count - 2).",
    )

    args = parser.parse_args()

    circuits_dir = args.circuits_dir
    limit = args.limit
    verbose = args.verbose
    mode = args.mode
    checkpoint_file = args.checkpoint_file
    num_workers = args.workers

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

    if num_workers is None:
        try:
            default_workers = max(1, mp.cpu_count() - 2)
            user_input = input(
                f"Enter number of workers [default: {default_workers}]: "
            ).strip()
            if user_input:
                try:
                    num_workers = int(user_input)
                except ValueError:
                    print(f"Invalid number. Defaulting to {default_workers}.")
                    num_workers = default_workers
            else:
                num_workers = default_workers
        except EOFError:
            num_workers = None

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
    print(f"Checkpoint File: {checkpoint_file}")
    print(f"Workers: {num_workers if num_workers else 'Auto'}")

    rerun_simulations_parallel(
        circuits_dir, limit, verbose, mode, checkpoint_file, num_workers
    )
