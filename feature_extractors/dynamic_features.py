from qiskit import QuantumCircuit
from feature_extractors.static_features import FeatureExtracter


class DynamicFeatureExtractor():
    def __init__(self, circuit: QuantumCircuit = None, feature_extractor: FeatureExtracter = None):
        """
        Initializes the DynamicFeatureExtractor with a given QuantumCircuit.
        Args:
            circuit (QuantumCircuit, optional): The quantum circuit to analyze.
        """
        self.feature_extractor = feature_extractor if feature_extractor else FeatureExtracter(circuit=circuit)
        self.extracted_features = self.feature_extractor.extracted_features
        self.circuit = circuit if circuit else self.feature_extractor.circuit
    
    def getSparsity(self):
        """
        Returns the sparsity of the circuit.
        Returns:
            dict: {"sparsity": float}
        """
        if "sparsity" in self.extracted_features:
            return {"sparsity": self.extracted_features["sparsity"]}
        if not self.circuit:
            self.extracted_features["sparsity"] = 0.0
            return {"sparsity": 0.0}
        
        num_qubits = self.circuit.num_qubits
        num_gates = len(self.circuit.data)
        sparsity = num_gates / (num_qubits * (num_qubits - 1)) if num_qubits > 1 else 0.0
        self.extracted_features["sparsity"] = sparsity
        return {"sparsity": sparsity}

    def extractAllFeatures(self):
        """
        Extracts all dynamic features from the circuit.
        Returns:
            dict: A dictionary containing all extracted dynamic features.
        """
        features = {}
        features.update(self.getSparsity())
        # Add more dynamic feature extraction methods as needed
        return features
    

    