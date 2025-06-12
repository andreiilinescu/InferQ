from qiskit import QuantumCircuit




def generate(n_qubits:int, measure:bool=False) -> QuantumCircuit:
    """
    Create an n-qubit GHZ state:
      |GHZ⟩ = (|0…0> + |1…1>)/√2
    """
    qc = QuantumCircuit(n_qubits, name=f"GHZ({n_qubits})")
    qc.h(0)
    for i in range(n_qubits - 1):
        qc.cx(i, i + 1)

    if measure:
        qc.measure_all()

    return qc
