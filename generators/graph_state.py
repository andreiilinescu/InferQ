from qiskit import QuantumCircuit


def generate(adjacency: list[list[int]]) -> QuantumCircuit:
    """Graph state from adjacency matrix."""
    n = len(adjacency)
    qc = QuantumCircuit(n, name="GraphState")
    for i in range(n):
        qc.h(i)
    for i in range(n):
        for j in range(i + 1, n):
            if adjacency[i][j]:
                qc.cz(i, j)
    return qc
