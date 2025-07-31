from generators.circuit_merger import CircuitMerger
from generators.lib.generator import BaseParams

from utils.save_utils import save_circuit_locally,create_circuits_table, save_circuit_metadata, upload_circuit_blob
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

def run_extraction_pipeline(circuitMerger:CircuitMerger,quantumSimulator:QuantumSimulator, conn):
    # generate Step
    circ=circuitMerger.generate_hierarchical_circuit()
    print(f"Generated circuit: {circ.num_qubits} qubits, depth {circ.depth()}, size {circ.size()}")
    
    # feature extraction step
    extracted_features=extract_features(circuit=circ)
    print(extracted_features)

    # simulation step
    res=quantumSimulator.simulate_all_methods(circ)
    print(res)

    # save step
    ## locally 
    qpy_hash,features,written=save_circuit_locally(circ,extracted_features,Path("./circuits/")) 
    
    ## remote
    if written:
        print(f"✓ Circuit saved with hash: {qpy_hash}")
        print(f"Serialization method: {features.get('serialization_method', 'unknown')}")
        # # save to blob
        # blob_path=upload_circuit_blob(container_client,circ,qpy_hash)
        # # save to db
        # features["blob_path"]=blob_path.split("circuits/")[1]
        # save_circuit_metadata(conn,features)
    


def main():
    seed=42
    # generate circuit
    # azure_conn=AzureConnection()
    # conn=azure_conn.get_conn()
    # container_client=azure_conn.get_container_client()
    # create_circuits_table(conn,FEATURES_LIST)

    base_params=BaseParams(max_qubits=100, min_qubits=100, max_depth=2000,min_depth=2000,seed=seed)
    circuitMerger=CircuitMerger(base_params=base_params)

    quantumSimulator = QuantumSimulator(seed=seed)
    
    run_extraction_pipeline(circuitMerger,quantumSimulator,None)
if __name__ == "__main__":
    main()
