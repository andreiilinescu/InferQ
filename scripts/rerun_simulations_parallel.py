import os
import sys

import argparse
import logging
import multiprocessing
import psutil
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
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
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("rerun_simulations_parallel.log"),
    ],
)
logger = logging.getLogger(__name__)
logging.getLogger("qiskit.passmanager.base_tasks").setLevel(logging.WARNING)
logging.getLogger("qiskit.compiler.transpiler").setLevel(logging.WARNING)

MEMORY_THRESHOLD_PERCENT = 90
MEMORY_CHECK_INTERVAL = 5


def process_circuit_file(file_path, mode, simulator):
    """
    Helper function to process a single circuit using an existing simulator instance.
    """
    try:
        # Load circuit
        with open(file_path, "rb") as f:
            circuits = qiskit.qpy.load(f)
            qc = circuits[0] if isinstance(circuits, list) else circuits

        # Extract hash from filename
        filename = os.path.basename(file_path)
        circuit_hash = os.path.splitext(filename)[0]

        updates = {}
        success_flag = False
        error_msg = None

        if mode == "auto":
            result = simulator.simulate_auto(qc)
            if result["success"]:
                success_flag = True
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
                success_flag = True
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
            "success": success_flag,
            "updates": updates,
            "error": error_msg,
            "file_path": file_path,
        }

    except Exception as e:
        return {
            "hash": None,
            "success": False,
            "updates": {},
            "error": str(e),
            "file_path": file_path,
        }


def process_folder(folder_path, mode, processed_hashes):
    """
    Worker function to process all circuits in a folder.
    """
    results = []
    try:
        # Initialize Simulator once per folder/worker
        simulator = QuantumSimulator(timeout_seconds=60)

        # List files in the folder
        try:
            files = [f for f in os.listdir(folder_path) if f.endswith(".qpy")]
        except FileNotFoundError:
            return []

        for filename in files:
            # Memory Hold-off
            while psutil.virtual_memory().percent > MEMORY_THRESHOLD_PERCENT:
                # Sleep to let memory clear up
                time.sleep(MEMORY_CHECK_INTERVAL)

            circuit_hash = os.path.splitext(filename)[0]

            # Skip if already processed
            if circuit_hash in processed_hashes:
                continue

            file_path = os.path.join(folder_path, filename)
            result = process_circuit_file(file_path, mode, simulator)
            results.append(result)

    except Exception as e:
        logger.error(f"Error processing folder {folder_path}: {e}")

    return results


def rerun_simulations_parallel(
    circuits_dir,
    limit=None,
    verbose=False,
    mode="auto",
    checkpoint_file="rerun_checkpoint.txt",
    num_workers=None,
):
    if not os.path.exists(circuits_dir):
        logger.error(f"Circuits directory not found: {circuits_dir}")
        return

    # Initialize Azure connection (Main Process)
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

    # Bucket processed hashes by folder prefix (first 2 chars)
    processed_buckets = {}
    if processed_hashes:
        logger.info("Bucketing processed hashes...")
        for h in processed_hashes:
            prefix = h[:2]
            if prefix not in processed_buckets:
                processed_buckets[prefix] = set()
            processed_buckets[prefix].add(h)

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

    # Determine workers
    if num_workers is None:
        num_workers = max(1, multiprocessing.cpu_count() - 1)

    logger.info(f"Starting parallel execution with {num_workers} workers.")

    # Open checkpoint file for appending
    if checkpoint_file:
        abs_checkpoint_path = os.path.abspath(checkpoint_file)
        logger.info(f"Opening checkpoint file at: {abs_checkpoint_path}")
        checkpoint_f = open(checkpoint_file, "a")
    else:
        checkpoint_f = None

    total_updated = 0

    try:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Submit tasks per folder
            future_to_folder = {}
            for folder_name in subdirs:
                folder_path = os.path.join(circuits_dir, folder_name)
                # Get relevant processed hashes for this folder
                folder_processed = processed_buckets.get(folder_name, set())

                future = executor.submit(
                    process_folder, folder_path, mode, folder_processed
                )
                future_to_folder[future] = folder_name

            # Process results as folders complete
            for future in tqdm(
                as_completed(future_to_folder),
                total=len(subdirs),
                desc="Processing Folders",
            ):
                folder_name = future_to_folder[future]
                try:
                    folder_results = future.result()
                    if verbose:
                        logger.info(
                            f"Folder {folder_name} returned {len(folder_results)} results."
                        )

                    # Process results for this folder
                    folder_updates_count = 0
                    for result in folder_results:
                        if limit and total_updated >= limit:
                            break

                        circuit_hash = result["hash"]
                        success = result["success"]
                        updates = result["updates"]
                        error = result["error"]

                        if success and circuit_hash:
                            if verbose:
                                logger.info(f"Success {circuit_hash}: {updates.keys()}")

                            # Update Azure Table
                            try:
                                table_success = update_circuit_metadata_in_table(
                                    table_client, circuit_hash, updates
                                )
                                if table_success:
                                    logger.info(
                                        f"\n----Updated table for {circuit_hash}----\n"
                                    )
                                    folder_updates_count += 1
                                    total_updated += 1
                                    if checkpoint_f:
                                        checkpoint_f.write(f"{circuit_hash}\n")
                                        checkpoint_f.flush()
                                else:
                                    logger.warning(
                                        f"Failed to update table for {circuit_hash} (table_success={table_success})"
                                    )
                            except Exception as e:
                                logger.error(
                                    f"Azure update error for {circuit_hash}: {e}"
                                )

                        elif error and verbose:
                            logger.warning(f"Failed {circuit_hash}: {error}")

                    if checkpoint_f:
                        checkpoint_f.flush()

                    if limit and total_updated >= limit:
                        logger.info(f"Limit of {limit} reached. Stopping.")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

                except Exception as e:
                    logger.error(f"Error processing folder {folder_name}: {e}")

    except KeyboardInterrupt:
        logger.info("Interrupted by user. Stopping...")
        executor.shutdown(wait=False, cancel_futures=True)
    finally:
        if checkpoint_f:
            checkpoint_f.close()

    logger.info(f"Rerun complete. Total circuits updated: {total_updated}")


if __name__ == "__main__":
    config = PipelineConfig()

    parser = argparse.ArgumentParser(
        description="Rerun simulations in parallel (folder-based) and update Azure Table."
    )
    parser.add_argument(
        "--circuits-dir", type=str, default=None, help="Directory containing circuits."
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
        "--workers", type=int, default=None, help="Number of worker processes."
    )

    args = parser.parse_args()

    circuits_dir = args.circuits_dir
    limit = args.limit
    verbose = args.verbose
    mode = args.mode
    checkpoint_file = args.checkpoint_file
    workers = args.workers

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

    if workers is None:
        try:
            default_workers = max(1, multiprocessing.cpu_count() - 1)
            user_input = input(
                f"Enter number of workers [default: {default_workers}]: "
            ).strip()
            if user_input:
                workers = int(user_input)
            else:
                workers = default_workers
        except:
            workers = None

    print(f"Circuits directory: {circuits_dir}")
    print(f"Limit: {limit if limit is not None else 'All'}")
    print(f"Mode: {mode}")
    print(f"Workers: {workers}")
    print(f"Checkpoint File: {checkpoint_file}")

    rerun_simulations_parallel(
        circuits_dir, limit, verbose, mode, checkpoint_file, workers
    )
