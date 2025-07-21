from pathlib import Path
from feature_extractors.graphs import *
import json, hashlib
from typing import Any
import inspect
from qiskit import QuantumCircuit
from feature_extractors.static_features import FeatureExtracter

class GraphFeatureExtracter(FeatureExtracter):
    def __init__(self, circuit: QuantumCircuit = None, feature_extractor: FeatureExtracter = None):
        self.feature_extractor = feature_extractor if feature_extractor else FeatureExtracter(circuit=circuit)
        self.extracted_features = self.feature_extractor.extracted_features
        self.circuit = circuit if circuit else self.feature_extractor.circuit
    
    def extractAllFeatures(self) -> dict[str, Any]:
        # We are going to extract using IGGraph
        iggraph = IGGraphExtractor(circuit=self.circuit, feature_extractor=self.feature_extractor)
        self.extracted_features = iggraph.extractAllFeatures()

        # We also need the basic size based features
        # from the QuantumGraph class
        # quantum_graph = QuantumGraph(circuit=self.circuit)
        # features.update(quantum_graph.extractAllFeatures())

        # We are also going to add the GDG based features
        # from the GDGGraph class

        # gdggraph = GDGGraph(circuit=self.circuit)
        # features.update(gdggraph.extractAllFeatures())

        return self.extracted_features



