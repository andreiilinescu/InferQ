from qiskit.circuit.random import random_circuit
from qiskit import QuantumCircuit


def generate(width: int, depth: int) -> QuantumCircuit:
    qc = random_circuit(width, depth * 2, measure=False, seed=10)
    qc.name = f"RandomCircuit{width}x{depth}"
    return qc
