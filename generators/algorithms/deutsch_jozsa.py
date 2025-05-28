import numpy as np
from qiskit.circuit import QuantumCircuit


def _build_oracle(n: int, balanced: bool, seed: int = 10) -> QuantumCircuit:
    """Construct the n-input + 1-output Deutsch-Jozsa oracle."""
    mode = "balanced" if balanced else "constant"
    oracle_qc = QuantumCircuit(n + 1, name=f"DJOracle({mode},{n})")
    rng = np.random.default_rng(seed)

    if balanced:
        # pick random bitstring b of length n
        b = rng.integers(0, 2, size=n)
        # apply X on inputs where b_i=1
        for i, bit in enumerate(b):
            if bit:
                oracle_qc.x(i)
        # compute f(x)=parity(b·x) into the ancilla
        for i in range(n):
            oracle_qc.cx(i, n)
        # undo the initial Xs
        for i, bit in enumerate(b):
            if bit:
                oracle_qc.x(i)
    else:
        # constant oracle: either always 0 (do nothing) or always 1 (flip ancilla)
        if rng.integers(2):
            oracle_qc.x(n)

    oracle_gate = oracle_qc.to_gate()
    oracle_gate.name = "Oracle"
    return oracle_gate


def _build_algorithm(oracle: QuantumCircuit, n: int) -> QuantumCircuit:
    """Assemble the full Deutsch-Jozsa circuit over n inputs + 1 ancilla."""
    dj_qc = QuantumCircuit(n + 1, n, name="Deutsch–Jozsa")
    # prepare ancilla in |1⟩ and put it into superposition
    dj_qc.x(n)
    dj_qc.h(n)
    # Hadamards on all input qubits
    for i in range(n):
        dj_qc.h(i)
    # oracle call
    dj_qc.append(oracle, range(n + 1))
    # Hadamards on inputs again
    for i in range(n):
        dj_qc.h(i)
    # barrier + measure inputs
    dj_qc.barrier()
    dj_qc.measure(range(n), range(n))
    return dj_qc


def generate(num_qubits: int, balanced: bool = True) -> QuantumCircuit:
    """
    Entry point for the Deutsch–Jozsa generator.

    Args:
        num_qubits: total qubits in the circuit (including the one ancilla).
        balanced:    if True, use a balanced oracle; otherwise constant.
    Returns:
        A QuantumCircuit of size num_qubits implementing Deutsch–Jozsa.
    """
    if num_qubits < 2:
        raise ValueError("Need at least 2 qubits (1 input + 1 ancilla).")
    # our helpers expect n = #inputs
    n_inputs = num_qubits - 1
    oracle_gate = _build_oracle(n_inputs, balanced)
    dj_circuit = _build_algorithm(oracle_gate, n_inputs)
    return dj_circuit
