# generators/grover_v_chain.py

from __future__ import annotations
import numpy as np
from qiskit import QuantumCircuit


def generate(num_qubits: int) -> QuantumCircuit:
    """
    Generate a Grover's algorithm circuit over `num_qubits` search qubits
    using the v-chain decomposition for multi-controlled gates (requires ancilla qubits).

    Args:
        num_qubits: Number of search qubits (>=1).

    Returns:
        QuantumCircuit implementing Grover's algorithm with v-chain ancilla strategy.
    """
    if num_qubits < 1:
        raise ValueError("Need at least 1 search qubit for Grover's algorithm.")

    n = num_qubits
    # v-chain requires n-2 ancilla qubits (0 if n<3)
    ancilla_count = max(0, n - 2)
    total_qubits = n + ancilla_count

    # create circuit with search qubits [0..n-1] and ancillas [n..]
    qc = QuantumCircuit(total_qubits, name="GroverVChain")
    search_qubits = list(range(n))
    ancillas = list(range(n, total_qubits))

    # 1) Prepare equal superposition on search qubits
    qc.h(search_qubits)

    # optimal number of Grover iterations
    iterations = int(np.floor(np.pi / 4 * np.sqrt(2**n)))

    for _ in range(iterations):
        # Oracle: phase flip on |11...1> using v-chain mct
        qc.h(search_qubits[-1])
        qc.mct(search_qubits[:-1], search_qubits[-1], ancillas, mode="v-chain")
        qc.h(search_qubits[-1])

        # Diffuser: inversion-about-mean
        qc.h(search_qubits)
        qc.x(search_qubits)
        qc.h(search_qubits[-1])
        qc.mct(search_qubits[:-1], search_qubits[-1], ancillas, mode="v-chain")
        qc.h(search_qubits[-1])
        qc.x(search_qubits)
        qc.h(search_qubits)

    # 3) Measure all search and ancilla qubits
    qc.measure_all()
    return qc
