from pathlib import Path
from feature_extractors.graphs import *
import json, hashlib
from typing import Any
import inspect
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag
from collections import Counter
import rustworkx as rx


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
    g = rx.PyGraph()
    g.add_nodes_from(range(circ.num_qubits))
    g.add_edges_from([(q, q2, v) for (q, q2), v in edges.items()])
    return g


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

    def getTwoQubitGateCount(self):
        if not self.circuit:
            return {"two_qubit_gate_count": 0}
        two_qubit_gates = [inst for inst in self.circuit.data if len(inst.qubits) == 2]
        return {"two_qubit_gate_count": len(two_qubit_gates)}

    def getTwoQubitGatePercentage(self):
        two_qubit_gates = self.getTwoQubitGateCount()["two_qubit_gate_count"]
        total_gates = len(self.circuit.data)
        percentage = (two_qubit_gates / total_gates) * 100 if total_gates > 0 else 0.0
        return {"two_qubit_gate_percentage": percentage}

    def extractAllFeatures(self) -> dict[str, Any]:
        features = {
            "num_qubits": self.getNumberOfQubits()["num_qubits"],
            "gate_counts": self.getGateCounts()["gate_counts"],
            "depth": self.getDepth()["depth"],
            "width": self.getWidth()["width"],
            "name": self.getName()["name"],
            "two_qubit_gate_count": self.getTwoQubitGateCount()["two_qubit_gate_count"],
            "two_qubit_gate_percentage": self.getTwoQubitGatePercentage()["two_qubit_gate_percentage"]
        }
        return features


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
    
    def getAverageDegree(self):
        if self.rustxgraph.num_nodes() == 0:
            return {"average_degree": 0.0}
        total_degree = sum(self.rustxgraph.degree(node) for node in range(self.rustxgraph.num_nodes()))
        average_degree = total_degree / self.rustxgraph.num_nodes()
        return {"average_degree": average_degree}


    def extractAllFeatures(self) -> dict[str, Any]:
        import inspect
        # Only get methods defined in IGGraph, not inherited
        methods = [
            getattr(self, name)
            for name, obj in self.__class__.__dict__.items()
            if inspect.isfunction(obj) and not name.startswith("__") and name != "extractAllFeatures"
        ]
        result = {}
        for method in methods:
            try:
                output = method()
                if isinstance(output, dict):
                    result.update(output)
            except Exception as e:
                print(f"Error in method {method.__name__}: {e}")
                continue  # Skip methods that raise exceptions
        return result