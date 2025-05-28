# generators/qft_entangled.py
from qiskit import QuantumCircuit
from .qft import generate as create_qft


def generate(n: int) -> QuantumCircuit:
    """
    Apply QFT to an n-qubit system in which we first
    prepare ⌊n/2⌋ Bell pairs on qubits (0,1), (2,3), ….
    """
    qc = QuantumCircuit(n, name=f"QFTEntangled({n})")

    # prepare ⌊n/2⌋ Bell pairs
    num_pairs = n // 2
    for i in range(num_pairs):
        qc.h(2 * i)
        qc.cx(2 * i, 2 * i + 1)

    # apply an n-qubit QFT
    qc.compose(create_qft(n), qubits=list(range(n)), inplace=True)

    return qc
