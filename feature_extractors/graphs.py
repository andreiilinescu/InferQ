from pathlib import Path
from feature_extractors.graphs import *
import json, hashlib
from typing import Any
import inspect
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag
from collections import Counter
import rustworkx as rx
import networkx as nx
import numpy as np


def convertToPyGraphIG(circ: QuantumCircuit) -> dict:
    """
    Converts a Qiskit QuantumCircuit to a rustworkx PyGraph.
    Each two-qubit gate is represented as an edge, with edge weights counting occurrences.
    Nodes correspond to qubits.
    Returns:
        rx.PyGraph: The constructed graph.
    """
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
        """
        Initializes the QuantumGraph with a given QuantumCircuit.
        Args:
            circuit (QuantumCircuit, optional): The quantum circuit to analyze.
        """
        self.circuit = circuit

    def getNumberOfQubits(self):
        """
        Returns the number of qubits in the circuit.
        Returns:
            dict: {"num_qubits": int}
        """
        return {"num_qubits": self.circuit.num_qubits} if self.circuit else {"num_qubits": 0}
    def getGateCounts(self):
        """
        Returns a count of each gate type in the circuit.
        Returns:
            dict: {"gate_counts": {str: int}}
        """
        if not self.circuit:
            return {"gate_counts": {}}
        gate_counts = Counter(instruction.operation.name for instruction in self.circuit.data)
        return {"gate_counts": dict(gate_counts)}
    def getDepth(self):
        """
        Returns the depth of the circuit.
        Returns:
            dict: {"depth": int}
        """
        return {"depth": self.circuit.depth()} if self.circuit else {"depth": 0}
    def getWidth(self):
        """
        Returns the width of the circuit.
        Returns:
            dict: {"width": int}
        """
        return {"width": self.circuit.width()} if self.circuit else {"width": 0}
    def getName(self):
        """
        Returns the name of the circuit.
        Returns:
            dict: {"name": str}
        """
        return {"name": self.circuit.name} if self.circuit else {"name": "Unnamed Circuit"}

    def getTwoQubitGateCount(self):
        """
        Returns the number of two-qubit gates in the circuit.
        Returns:
            dict: {"two_qubit_gate_count": int}
        """
        if not self.circuit:
            return {"two_qubit_gate_count": 0}
        two_qubit_gates = [inst for inst in self.circuit.data if len(inst.qubits) == 2]
        return {"two_qubit_gate_count": len(two_qubit_gates)}

    def getTwoQubitGatePercentage(self):
        """
        Returns the percentage of two-qubit gates in the circuit.
        Returns:
            dict: {"two_qubit_gate_percentage": float}
        """
        two_qubit_gates = self.getTwoQubitGateCount()["two_qubit_gate_count"]
        total_gates = len(self.circuit.data)
        percentage = (two_qubit_gates / total_gates) * 100 if total_gates > 0 else 0.0
        return {"two_qubit_gate_percentage": percentage}

    def extractAllFeatures(self) -> dict[str, Any]:
        """
        Extracts all basic features from the quantum circuit.
        Returns:
            dict: All extracted features.
        """
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
        """
        Initializes the IGGraph with a QuantumCircuit.
        Converts the circuit to a rustworkx graph and precomputes shortest path distances.
        Args:
            circuit (QuantumCircuit): The quantum circuit to analyze.
        """
        super().__init__(circuit)
        self.rustxgraph = convertToPyGraphIG(circuit)
        self.distances = rx.floyd_warshall(self.rustxgraph, weight_fn=float)
        # self.nxgraph = rx.networkx_converter(self.rustxgraph)

    def getRadius(self):
        """
        Returns the radius of the graph (minimum eccentricity).
        Returns:
            dict: {"radius": float}
        """
        # Use precomputed distances
        radius = min(
            max(self.distances[node].values()) for node in self.distances if self.distances[node]
        )
        return {"radius": radius}
    
    def getDiameter(self):
        """
        Returns the diameter of the graph (maximum shortest path length).
        Returns:
            dict: {"diameter": float}
        """
        # Use precomputed distances
        diameter = max(
            dist
            for row in self.distances.values()
            for dist in row.values()
            if dist is not None
        )
        return {"diameter": diameter}
    
    def getConnectedComponents(self):
        """
        Returns the connected components of the graph.
        Returns:
            dict: {"connected_components": list[list[int]]}
        """
        components = rx.connected_components(self.rustxgraph)
        return {"connected_components": [list(comp) for comp in components]}

    def getMaxDegree(self):
        """
        Returns the maximum degree of any node in the graph.
        Returns:
            dict: {"max_degree": int}
        """
        degrees = [self.rustxgraph.degree(node) for node in range(self.circuit.num_qubits)]
        max_deg = max(degrees) if degrees else 0
        return {"max_degree": int(max_deg)}

    def getMinCut(self):
        """
        Returns the upper bound of the minimum cut of the graph.
        Returns:
            dict: {"min_cut_upper": int}
        """
        min_cut = rx.stoer_wagner_min_cut(self.rustxgraph)[0] if self.rustxgraph.num_edges() else 0
        return {"min_cut_upper": int(min_cut)}

    def getEdgeCount(self):
        """
        Returns the number of edges in the graph.
        Returns:
            dict: {"edge_count": int}
        """
        edge_count = self.rustxgraph.num_edges() if self.rustxgraph else 0
        return {"edge_count": int(edge_count)}

    def getNodeCount(self):
        """
        Returns the number of nodes in the graph.
        Returns:
            dict: {"node_count": int}
        """
        node_count = self.rustxgraph.num_nodes() if self.rustxgraph else 0
        return {"node_count": int(node_count)}
    
    def getAverageDegree(self):
        """
        Returns the average degree of nodes in the graph.
        Returns:
            dict: {"average_degree": float}
        """
        if self.rustxgraph.num_nodes() == 0:
            return {"average_degree": 0.0}
        total_degree = sum(self.rustxgraph.degree(node) for node in range(self.rustxgraph.num_nodes()))
        average_degree = total_degree / self.rustxgraph.num_nodes()
        return {"average_degree": average_degree}
    
    def getStandardDeviationAdjacencyMatrix(self):
        """
        Returns the standard deviation of the adjacency matrix values.
        Returns:
            dict: {"std_dev_adjacency_matrix": float}
        """
        if self.rustxgraph.num_nodes() == 0:
            return {"std_dev_adjacency_matrix": 0.0}
        adjacency_matrix = rx.adjacency_matrix(self.rustxgraph, weight_fn=float)
        std_dev = np.std(adjacency_matrix)
        return {"std_dev_adjacency_matrix": std_dev}

    def getCentralPointOfDominence(self):
        """
        Returns the maximum betweenness centrality value in the graph.
        Returns:
            dict: {"central_point_of_dominance": float}
        """
        if self.rustxgraph.num_nodes() == 0:
            return {"central_point_of_dominance": 0.0}
        centrality = rx.betweenness_centrality(self.rustxgraph, normalized=True)
        max_centrality = max(centrality.values())
        return {"central_point_of_dominance": max_centrality}
    
    def getCoreNumber(self):
        """
        Returns the core number for each node in the graph.
        Returns:
            dict: {"core_number": dict}
        """
        if self.rustxgraph.num_nodes() == 0:
            return {"core_number": {}}
        core_numbers = rx.core_number(self.rustxgraph)
        return {"core_number": dict(enumerate(core_numbers))}

    def getAverageClusteringCoefficient(self):
        """
        Returns the average clustering coefficient (transitivity) of the graph.
        Returns:
            dict: {"average_clustering_coefficient": float}
        """
        # Let us use transitivity function
        if self.rustxgraph.num_nodes() == 0:
            return {"average_clustering_coefficient": 0.0} 
        coeff = rx.transitivity(self.rustxgraph)
        return {"average_clustering_coefficient": coeff}
    

    def getAverageShortestPathLength(self):
        """
        Returns the average shortest path length between all pairs of nodes.
        Returns:
            dict: {"average_shortest_path_length": float}
        """
        # Use precomputed distances
        if self.rustxgraph.num_nodes() == 0:    
            return {"average_shortest_path_length": 0.0}
        total_length = 0
        count = 0
        for node, dist_dict in self.distances.items():
            for target, length in dist_dict.items():
                if length is not None and node != target:
                    total_length += length
                    count += 1
        average_length = total_length / count if count > 0 else 0.0
        return {"average_shortest_path_length": average_length}
        
    def extractAllFeatures(self) -> dict[str, Any]:
        """
        Extracts all features defined in IGGraph and returns them as a single dictionary.
        Returns:
            dict: All extracted features.
        """
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