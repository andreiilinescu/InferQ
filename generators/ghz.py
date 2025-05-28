from qiskit import QuantumCircuit


def generate(n):
    """
    Create an n-qubit GHZ state:
      |GHZ⟩ = (|0…0> + |1…1>)/√2
    """
    qc = QuantumCircuit(n, name=f"GHZ({n})")
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    return qc
