from collections import Counter
from pathlib import Path
import json, hashlib, gzip, uuid, qiskit
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag
import retworkx as rx



# class QuantumGraph

# class IGGraph(QuantumGraph)



# ───────────────────────────────────────── graph-based features

def convertToPyGraphIG(circ: QuantumCircuit) -> dict:
    dag = circuit_to_dag(circ)
    alledges = [
        tuple(sorted((q, q2)))
        for gate in dag.two_qubit_ops()
        for (q, q2) in [tuple(sorted([q._index for q in gate.qargs]))]
    ]
    edges = {}
    for edge in alledges:
        if edge in edges.keys():
            edges[edge] += 1
        else:
            edges[edge] = 1
    try:
        import rustworkx as rx
    except ImportError:
        import retworkx as rx
    g = rx.PyGraph()
    g.add_nodes_from(range(circ.num_qubits))
    g.add_edges_from([(q, q2, v) for (q, q2), v in edges.items()])
    return g

def getDiameter(graph, circuit):
    # Compute all-pairs shortest path lengths
    distances = rx.floyd_warshall(graph, weight_fn=float)

    # Find the diameter
    diameter = max(
        dist
        for row in distances.values()
        for dist in row.values()
        if dist is not None
    )
    return {"diameter":diameter}


def getMinCutDegree(g: rx.PyGraph, circ: QuantumCircuit):
    degrees = [g.degree(node) for node in range(circ.num_qubits)]
    max_deg = max(degrees) if degrees else 0
    min_cut = rx.stoer_wagner_min_cut(g)[0] if g.num_edges() else 0
    return {"max_degree": int(max_deg), "min_cut_upper": int(min_cut)}
