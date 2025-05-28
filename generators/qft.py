from qiskit import QuantumCircuit
import numpy as np


def generate(n_qubits: int) -> QuantumCircuit:
    """Create a Quantum Fourier Transform circuit.

    Args:
        n_qubits: Number of qubits

    Returns:
        QuantumCircuit: QFT circuit
    """
    circuit = QuantumCircuit(n_qubits, name=f"QFT({n_qubits})")

    # Apply QFT
    for i in range(n_qubits):
        # Apply Hadamard gate
        circuit.h(i)

        # Apply controlled phase gates
        for j in range(i + 1, n_qubits):
            angle = np.pi / (2 ** (j - i))
            circuit.cp(angle, j, i)

    # Swap qubits to get correct order
    for i in range(n_qubits // 2):
        circuit.swap(i, n_qubits - 1 - i)

    return circuit
