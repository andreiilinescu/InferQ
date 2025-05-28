from __future__ import annotations
import numpy as np
from qiskit import QuantumCircuit


def _oracle_phase_flip(n: int) -> QuantumCircuit:
    """
    Construct a phase flip oracle on n qubits that marks the |11...1> state
    by applying a Z-phase if all qubits are 1, using no extra ancilla.
    """
    qc = QuantumCircuit(n, name="OraclePhaseFlip")
    # Multi-controlled phase flip via relative-phase implementation
    # Use a chain of CZ gates and H on last qubit
    qc.h(n - 1)
    # Controlled-Z from all other qubits onto last qubit
    qc.mcp(np.pi, list(range(n - 1)), n - 1)
    qc.h(n - 1)
    return qc


def _diffuser(n: int) -> QuantumCircuit:
    """
    Construct the diffusion operator (inversion about the mean) on n qubits
    without ancilla qubits.
    """
    qc = QuantumCircuit(n, name="Diffuser")
    # Step 1: H on all qubits
    qc.h(range(n))
    # Step 2: X on all qubits
    qc.x(range(n))
    # Step 3: phase flip on |11...1>
    qc.h(n - 1)
    qc.mcp(np.pi, list(range(n - 1)), n - 1)
    qc.h(n - 1)
    # Step 4: X on all qubits
    qc.x(range(n))
    # Step 5: H on all qubits
    qc.h(range(n))
    return qc


def generate(num_qubits: int) -> QuantumCircuit:
    """
    Generate a Grover's algorithm circuit over num_qubits search qubits,
    marking the all-ones state, using no ancilla qubits.

    Args:
        num_qubits: Number of search qubits (>=1).

    Returns:
        QuantumCircuit implementing the no-ancilla Grover's algorithm.
    """
    if num_qubits < 1:
        raise ValueError("Need at least 1 qubit for Grover's search.")

    n = num_qubits
    # Calculate optimal number of iterations
    iterations = int(np.floor(np.pi / 4 * np.sqrt(2**n)))

    # Initialize circuit
    qc = QuantumCircuit(n, name="GroverNoAncilla")
    # 1) Prepare equal superposition
    qc.h(range(n))

    # Build oracle and diffuser
    oracle = _oracle_phase_flip(n)
    diffuser = _diffuser(n)

    # 2) Grover iterations
    for _ in range(iterations):
        qc.compose(oracle, inplace=True)
        qc.compose(diffuser, inplace=True)

    # 3) Measure all qubits
    qc.measure_all()
    return qc
