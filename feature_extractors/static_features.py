from qiskit import QuantumCircuit


# ───────────────────────────────────────── static features
def static_features(circ: QuantumCircuit) -> dict:
    counts = circ.count_ops()
    return {
        "n_qubits": circ.num_qubits,
        "depth": circ.depth(),
        "two_qubit_gates": sum(1 for op in circ.data if len(op[1]) == 2),
        "t_count": counts.get("t", 0),
        "h_count": counts.get("h", 0),
    }
