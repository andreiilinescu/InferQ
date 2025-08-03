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

def run_extraction_pipeline(circuitMerger: CircuitMerger, quantumSimulator: QuantumSimulator, azure_conn: AzureConnection = None):
    # generate Step
    circ = circuitMerger.generate_hierarchical_circuit()
    print(f"Generated circuit: {circ.num_qubits} qubits, depth {circ.depth()}, size {circ.size()}")
    
    # feature extraction step
    extracted_features = extract_features(circuit=circ)
    print("Extracted features:", extracted_features)

    # simulation step 
    res = quantumSimulator.simulate_all_methods(circ)

    # save step
    ## locally 
    qpy_hash, features, written = save_circuit_locally(circ, extracted_features, Path("./circuits/")) 
    
    ## remote (Azure Table Storage)
    if written and azure_conn:
        print(f"✓ Circuit saved locally with hash: {qpy_hash}")
        print(f"Serialization method: {features.get('serialization_method', 'unknown')}")
        
        try:
            # Save to blob storage
            container_client = azure_conn.get_container_client()
            serialization_method = features.get('serialization_method', 'qpy')
            blob_path = upload_circuit_blob(container_client, circ, qpy_hash, serialization_method)
            features["blob_path"] = blob_path.split("circuits/")[1] if "circuits/" in blob_path else blob_path
            print(f"✓ Circuit uploaded to blob storage: {blob_path}")
            
            # Save metadata to Azure Table Storage (NEW: replaces SQL Database)
            table_client = azure_conn.get_circuits_table_client()
            table_success = save_circuit_metadata_to_table(table_client, features)
            
            if table_success:
                print("✓ Circuit metadata saved to Azure Table Storage")
            else:
                print("✗ Failed to save metadata to Azure Table Storage")
                
        except Exception as e:
            print(f"✗ Error saving to Azure: {e}")
    elif written:
        print(f"✓ Circuit saved locally with hash: {qpy_hash}")
        print("Azure connection not provided - skipping cloud storage")
    


def main():
    seed = 42
    
    # Initialize Azure connection for cloud storage
    try:
        azure_conn = AzureConnection()
        print("✓ Connected to Azure services (Table Storage + Blob Storage)")
    except Exception as e:
        print(f"⚠️  Azure connection failed: {e}")
        print("Continuing with local storage only...")
        azure_conn = None

    # Configure circuit generation
    base_params = BaseParams(max_qubits=5, min_qubits=1, max_depth=2000, min_depth=1, seed=seed)
    circuitMerger = CircuitMerger(base_params=base_params)

    # Initialize quantum simulator
    quantumSimulator = QuantumSimulator(seed=seed)
    
    # Run the extraction pipeline
    run_extraction_pipeline(circuitMerger, quantumSimulator, azure_conn)
if __name__ == "__main__":
    main()
