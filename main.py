from generators.circuit_merger import CircuitMerger
from generators.lib.generator import BaseParams

from utils.save_utils import (
    save_circuit_locally,
    save_circuit_metadata_to_table,
    upload_circuit_blob
)
from utils.azure_connection import AzureConnection
from utils.features_const import FEATURES_LIST

from feature_extractors.extractors import extract_features
from simulators.simulate import QuantumSimulator

from pathlib import Path
import logging

from qiskit_aer import AerSimulator

# Suppress verbose Qiskit logging
logging.getLogger('qiskit').setLevel(logging.WARNING)
logging.getLogger('qiskit.passmanager').setLevel(logging.WARNING)
logging.getLogger('qiskit.compiler').setLevel(logging.WARNING)
logging.getLogger('qiskit.transpiler').setLevel(logging.WARNING)
logging.getLogger('qiskit_aer').setLevel(logging.WARNING)

# Suppress verbose Azure logging
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('azure.storage.blob').setLevel(logging.WARNING)
logging.getLogger('azure.data.tables').setLevel(logging.WARNING)
logging.getLogger('azure.core').setLevel(logging.WARNING)

# Configure main logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_extraction_pipeline(circuitMerger: CircuitMerger, quantumSimulator: QuantumSimulator, azure_conn: AzureConnection = None):
    logger.info("=" * 60)
    logger.info("STARTING QUANTUM CIRCUIT EXTRACTION PIPELINE")
    logger.info("=" * 60)
    
    # Step 1: Circuit Generation
    logger.info("STEP 1: Circuit Generation")
    logger.info("-" * 30)
    try:
        circ = circuitMerger.generate_hierarchical_circuit()
        logger.info(f"✓ Generated circuit: {circ.num_qubits} qubits, depth {circ.depth()}, size {circ.size()}")
    except Exception as e:
        logger.error(f"Circuit generation failed: {e}")
        raise
    
    # Step 2: Feature Extraction
    logger.info("\nSTEP 2: Feature Extraction")
    logger.info("-" * 30)
    try:
        extracted_features = extract_features(circuit=circ)
        logger.info(f"✓ Feature extraction completed: {len(extracted_features)} features")
        logger.debug(f"Feature keys: {list(extracted_features.keys())}")
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        raise

    # Step 3: Quantum Simulation
    logger.info("\nSTEP 3: Quantum Simulation")
    logger.info("-" * 30)
    try:
        res = quantumSimulator.simulate_all_methods(circ)
        successful_sims = sum(1 for r in res.values() if r.get('success', False))
        total_sims = len(res)
        logger.info(f"✓ Simulation completed: {successful_sims}/{total_sims} methods successful")
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise
    
    # Step 3.5: Process Simulation Data
    logger.info("\nSTEP 3.5: Processing Simulation Data")
    logger.info("-" * 30)
    try:
        from simulators.simulation_utils import process_simulation_data_for_features
        combined_features = process_simulation_data_for_features(res, extracted_features)
    except Exception as e:
        logger.error(f"Simulation data processing failed: {e}")
        # Continue with just extracted features if simulation data processing fails
        combined_features = extracted_features
    
    # Step 4: Local Storage
    logger.info("\nSTEP 4: Local Storage")
    logger.info("-" * 30)
    try:
        qpy_hash, features, written = save_circuit_locally(circ, combined_features, Path("./circuits/"))
        if written:
            logger.info(f"✓ Circuit saved locally with hash: {qpy_hash}")
            logger.info(f"✓ Serialization method: {features.get('serialization_method', 'unknown')}")
        else:
            logger.info(f"Circuit {qpy_hash} already exists locally")
    except Exception as e:
        logger.error(f"Local storage failed: {e}")
        raise
    
    # Step 5: Cloud Storage (if available)
    if written and azure_conn:
        logger.info("\nSTEP 5: Cloud Storage")
        logger.info("-" * 30)
        
        try:
            # Sub-step 5a: Blob Storage
            logger.info("5a. Uploading to Azure Blob Storage...")
            container_client = azure_conn.get_container_client()
            serialization_method = features.get('serialization_method', 'qpy')
            blob_path = upload_circuit_blob(container_client, circ, qpy_hash, serialization_method)
            features["blob_path"] = blob_path.split("circuits/")[1] if "circuits/" in blob_path else blob_path
            logger.info(f"✓ Circuit uploaded to blob storage")
            
            # Sub-step 5b: Table Storage
            logger.info("5b. Saving metadata to Azure Table Storage...")
            table_client = azure_conn.get_circuits_table_client()
            table_success = save_circuit_metadata_to_table(table_client, features)
            
            if table_success:
                logger.info("✓ Circuit metadata saved to Azure Table Storage")
            else:
                logger.error("✗ Failed to save metadata to Azure Table Storage")
                
        except Exception as e:
            logger.error(f"Cloud storage failed: {e}")
            logger.info("Circuit is still available locally")
            
    elif written:
        logger.info("\nSTEP 5: Cloud Storage")
        logger.info("-" * 30)
        logger.info("Azure connection not provided - skipping cloud storage")
    elif azure_conn:
        logger.info("\nSTEP 5: Cloud Storage")
        logger.info("-" * 30)
        logger.info("Circuit already exists - skipping cloud storage")
    
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)


def main():
    logger.info("🚀 Starting Quantum Circuit Processing Application")
    logger.info("=" * 80)
    
    seed = 21384
    logger.info(f"Using random seed: {seed}")
    
    # Initialize Azure connection for cloud storage
    logger.info("\nInitializing Azure Connection...")
    try:
        azure_conn = AzureConnection()
        logger.info("✓ Connected to Azure services (Table Storage + Blob Storage)")
    except Exception as e:
        logger.warning(f"Azure connection failed: {e}")
        logger.info("Continuing with local storage only...")
        azure_conn = None

    # Configure circuit generation
    logger.info("\nConfiguring Circuit Generation...")
    base_params = BaseParams(max_qubits=5, min_qubits=1, max_depth=2000, min_depth=1, seed=seed,measure=False)
    logger.info(f"Circuit parameters: {base_params.min_qubits}-{base_params.max_qubits} qubits, {base_params.min_depth}-{base_params.max_depth} depth")
    
    try:
        circuitMerger = CircuitMerger(base_params=base_params)
        logger.info("✓ Circuit merger initialized")
    except Exception as e:
        logger.error(f"Failed to initialize circuit merger: {e}")
        raise

    # Initialize quantum simulator
    logger.info("\nInitializing Quantum Simulator...")
    try:
        quantumSimulator = QuantumSimulator(seed=seed, shots=None)
        logger.info("✓ Quantum simulator initialized")
    except Exception as e:
        logger.error(f"Failed to initialize quantum simulator: {e}")
        raise
    
    # Run the extraction pipeline
    logger.info("\nStarting Pipeline Execution...")
    try:
        run_extraction_pipeline(circuitMerger, quantumSimulator, azure_conn)
        logger.info("\n🎉 Application completed successfully!")
    except Exception as e:
        logger.error(f"\n💥 Application failed: {e}")
        raise
if __name__ == "__main__":
    main()
