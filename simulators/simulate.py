from qiskit import transpile
from qiskit.circuit import QuantumCircuit
from qiskit_aer import AerSimulator

 
def simulate(qc:QuantumCircuit, simulator: AerSimulator) -> float:
    qc = transpile(qc, simulator)
    res=simulator.run(qc).result()
    return res
