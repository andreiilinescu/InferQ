from collections import Counter
from pathlib import Path
import json, hashlib, gzip, uuid, qiskit
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag
import retworkx as rx


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
