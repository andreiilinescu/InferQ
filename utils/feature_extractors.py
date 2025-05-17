"""
Light-weight, import-anywhere feature extractors.

Usage:
    from inferq_dataset.feature_extractors import extract_all
    feats  = extract_all(my_circuit)
"""

from collections import Counter
from pathlib import Path
import json, hashlib, gzip, uuid, qiskit
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag
import retworkx as rx
import numpy as np


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


# ───────────────────────────────────────── graph-based features
def graph_features(circ: QuantumCircuit) -> dict:
    dag = circuit_to_dag(circ)
    edges = {
        (q, q2)
        for gate in dag.two_qubit_ops()
        for (q, q2) in [tuple(sorted([q._index for q in gate.qargs]))]
    }
    try:
        import rustworkx as rx
    except ImportError:
        import retworkx as rx
    g = rx.PyGraph()
    g.add_nodes_from(range(circ.num_qubits))
    g.add_edges_from([(q, q2, None) for (q, q2) in edges])

    degrees = [g.degree(node) for node in range(circ.num_qubits)]
    max_deg = max(degrees) if degrees else 0
    min_cut = rx.stoer_wagner_min_cut(g)[0] if g.num_edges() else 0
    return {"max_degree": int(max_deg), "min_cut_upper": int(min_cut)}


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


def dynamic_probes(circ):
    return {
        "sparsity_est": probe_sparsity(circ),
        "bond_dim_est": probe_bond_dim(circ),
    }


# ───────────────────────────────────────── single entry-point
def extract_all(circ: QuantumCircuit) -> dict:
    feats = {}
    for fn in (static_features, graph_features):
        feats.update(fn(circ))
    return feats
