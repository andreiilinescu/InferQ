from collections import Counter
from pathlib import Path
import json, hashlib, gzip, uuid, qiskit
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag
import retworkx as rx
import numpy as np


# ───────────────────────────────────────── dynamic probes (cheap)
def probe_sparsity(circ: QuantumCircuit, limit: int = 100_000) -> int:
    """Run a sparse simulator until support exceeds `limit` amplitudes."""
    from qiskit_aer import Aer

    backend = Aer.get_backend("aer_simulator_statevector")
    backend.set_options(method="statevector", max_parallel_threads=1)
    qc = circ.copy()
    qc.save_statevector()
    n_support = 2**circ.num_qubits  # pessimistic start
    try:
        result = backend.run(qc, shots=0, optimization_level=0).result()
        state = result.get_statevector(qc)
        n_support = np.count_nonzero(np.abs(state) > 1e-12)
    except MemoryError:
        pass  # aborted → keep pessimistic number
    return int(min(n_support, limit * 10))


def probe_bond_dim(circ: QuantumCircuit, cap: int = 64) -> int:
    """Run MPS sim with capped bond; return max bond reached or cap+."""
    from qiskit_aer import Aer

    backend = Aer.get_backend("aer_simulator")
    backend.set_options(
        method="matrix_product_state", max_bond_dimension=cap, max_parallel_threads=1
    )
    qc = circ.copy()
    qc.save_expectation_value(
        pauli="Z" * circ.num_qubits, qubits=list(range(circ.num_qubits))
    )
    try:
        result = backend.run(qc, shots=0).result()
        meta = result.results[0].metadata
        max_bond = meta.get("max_bond_dimension", cap + 1)
    except Exception:
        max_bond = cap + 1
    return int(max_bond)


def dynamic_features(circ):
    return {
        "sparsity_est": probe_sparsity(circ),
        "bond_dim_est": probe_bond_dim(circ),
    }
