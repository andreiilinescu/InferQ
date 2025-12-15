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


def rerun_simulations(circuits_dir, limit=None):
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

            # Run auto simulation
            logger.info(f"Simulating {circuit_hash}...")
            result = simulator.simulate_auto(qc)

            if result["success"]:
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

                # Update Azure Table
                success = update_circuit_metadata_in_table(
                    table_client, circuit_hash, updates
                )
                if success:
                    count += 1
                else:
                    logger.warning(f"Failed to update table for {circuit_hash}")
            else:
                logger.warning(
                    f"Simulation failed for {circuit_hash}: {result.get('error')}"
                )

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
        default=str(config.circuits_dir),
        help="Directory containing circuits.",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Maximum number of circuits to process."
    )

    args = parser.parse_args()

    rerun_simulations(args.circuits_dir, args.limit)
