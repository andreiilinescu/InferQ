from pathlib import Path
from feature_extractors.graphs import *
import json, hashlib
from typing import Any
import inspect


class FeatureExtracter():
    def __init__(self, circuit: QuantumCircuit = None):
        self.circuit = circuit

class GraphFeatureExtracter(FeatureExtracter):
    def __init__(self, circuit: QuantumCircuit = None):
        super().__init__(circuit)
    
    def extractAllFeatures(self) -> dict[str, Any]:
        # We are going to extract using IGGraph
        iggraph = IGGraph(circuit=self.circuit)
        features = iggraph.extractAllFeatures()

        # We also need the basic size based features
        # from the QuantumGraph class
        quantum_graph = QuantumGraph(circuit=self.circuit)
        features.update(quantum_graph.extractAllFeatures())

        # We are also going to add the GDG based features
        # from the GDGGraph class

        # gdggraph = GDGGraph(circuit=self.circuit)
        # features.update(gdggraph.extractAllFeatures())

        return features



