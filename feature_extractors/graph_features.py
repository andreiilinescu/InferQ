from collections import Counter
from pathlib import Path
import json, hashlib, gzip, uuid, qiskit
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag
import retworkx as rx
from typing import Any


# ───────────────────────────────────────── graph-based features

class QuantumGraph:
    
    def __init__(self, circuit: QuantumCircuit = None):
        self.circuit = circuit
    
    def getNumberOfQubits(self):
        return {"num_qubits": self.circuit.num_qubits} if self.circuit else {"num_qubits": 0}
    def getGateCounts(self):
        if not self.circuit:
            return {"gate_counts": {}}
        gate_counts = Counter(instruction.operation.name for instruction in self.circuit.data)
        return {"gate_counts": dict(gate_counts)}
    def getDepth(self):
        return {"depth": self.circuit.depth()} if self.circuit else {"depth": 0}
    def getWidth(self):
        return {"width": self.circuit.width()} if self.circuit else {"width": 0}
    def getName(self):
        return {"name": self.circuit.name} if self.circuit else {"name": "Unnamed Circuit"}
    
class IGGraph(QuantumGraph):

    def __init__(self, circuit : QuantumCircuit):
        super().__init__(circuit)
        self.rustxgraph = convertToPyGraphIG(circuit)
    
    def getDiameter(self):
        # Compute all-pairs shortest path lengths
        distances = rx.floyd_warshall(self.rustxgraph, weight_fn=float)

        # Find the diameter
        diameter = max(
            dist
            for row in distances.values()
            for dist in row.values()
            if dist is not None
        )
        return {"diameter":diameter}

    def getMaxDegree(self):
        self.rustxgraph = None
        degrees = [self.rustxgraph.degree(node) for node in range(self.circuit.num_qubits)]
        max_deg = max(degrees) if degrees else 0
        return {"max_degree": int(max_deg)}

    def getMinCut(self):
        min_cut = rx.stoer_wagner_min_cut(self.rustxgraph)[0] if self.rustxgraph.num_edges() else 0
        return {"min_cut_upper": int(min_cut)}

    def getEdgeCount(self):
        edge_count = self.rustxgraph.num_edges() if self.rustxgraph else 0
        return {"edge_count": int(edge_count)}
    def getNodeCount(self):
        node_count = self.rustxgraph.num_nodes() if self.rustxgraph else 0
        return {"node_count": int(node_count)}
    def getEdgeWeights(self):
        if not self.rustxgraph:
            return {"edge_weights": {}}
        edge_weights = {edge: weight for edge, weight in self.rustxgraph.edge_weights()}
        return {"edge_weights": edge_weights}

    def extractAllFeatures(self) -> dict[str, Any]: 
        import inspect
        # Get all bound methods except __init__ and this one
        methods = [
            method for name, method in inspect.getmembers(self, predicate=inspect.ismethod)
            if not name.startswith("__") and name != "extractAllFeatures"
        ]
        result = {}
        for method in methods:
            try:
                output = method()
                if isinstance(output, dict):
                    result.update(output)
            except Exception as e:
                continue  # Skip methods that raise exceptions
        return result




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
