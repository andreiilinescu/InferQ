from generators.circuit_merger import CircuitMerger
from generators.lib.generator import BaseParams
from utils.save_utils import save_circuit_locally,create_circuits_table, save_circuit_metadata, upload_circuit_blob
from utils.azure_connection import AzureConnection
from utils.features_const import FEATURES_LIST
from pathlib import Path
from simulators.simulate import simulate

from qiskit_aer import AerSimulator
def main():
    # generate circuit
    azure_conn=AzureConnection()
    conn=azure_conn.get_conn()
    container_client=azure_conn.get_container_client()
    create_circuits_table(conn,FEATURES_LIST)

    base_params=BaseParams(max_qubits=10, min_qubits=2, max_depth=100,min_depth=2, seed=42)
    circuitMerger=CircuitMerger(base_params=base_params)
    circ=circuitMerger.generate_hierarchical_circuit()
    extracted_features={}
    # save locally 
    qpy_hash,features,written=save_circuit_locally(circ,extracted_features,Path("./circuits/")) 
    # save to blob
    if(written):
        blob_path=upload_circuit_blob(container_client,circ,qpy_hash)
        # save to db
        features["blob_path"]=blob_path.split("circuits/")[1]
        save_circuit_metadata(conn,features)
    
    
    #save simulation data
    res=simulate(circ,AerSimulator()).to_dict()
    metadata=res["metadata"]
    time_taken=res["time_taken"]
    max_mem_mb=metadata["max_memory_mb"]

if __name__ == "__main__":
    main()
