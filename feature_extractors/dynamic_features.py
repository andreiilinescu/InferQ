from qiskit import QuantumCircuit
from feature_extractors.static_features import FeatureExtracter

from typing import Any
import logging

# Configure logging
logger = logging.getLogger(__name__)

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

    def getQuantumLocalityRatio(self):
        '''
        This measure the ratio between number of gates acting on local qubits vs long ditance ones. So if gates act on qubits that are close to each other, the locality ratio will be high.
        Returns:
            dict: {"locality_ratio": float}
        '''
        if "locality_ratio" in self.extracted_features:
            return {"locality_ratio": self.extracted_features["locality_ratio"]}
        if not self.circuit:
            self.extracted_features["locality_ratio"] = 0.0
            return {"locality_ratio": 0.0}
        num_qubits = self.circuit.num_qubits
        num_gates = len(self.circuit.data)
        if num_qubits < 2:
            self.extracted_features["locality_ratio"] = 0.0
            return {"locality_ratio": 0.0}
        # for each gate, extracting the qubit indices
        # then check if they are all adjacent qubits. If not, then it is a long distance gate
        long_distance_gates = 0
        local_gates = 0
        for gate in self.circuit.data:
            qubits = [int(str(qubit).split("index=")[1].split(")")[0].split(">")[0]) for qubit in gate[1]]
            if len(qubits) < 2:
                local_gates += 1
                continue
            if all(abs(qubits[i] - qubits[i + 1]) == 1 for i in range(len(qubits) - 1)):
                local_gates += 1
            else:
                long_distance_gates += 1
        locality_ratio = local_gates / (local_gates + long_distance_gates) if (local_gates + long_distance_gates) > 0 else 0.0
        self.extracted_features["locality_ratio"] = locality_ratio
        return {"locality_ratio": locality_ratio}


    def extractAllFeatures(self) -> dict[str, Any]:
        """
        Extracts all basic features from the quantum circuit.
        If a feature method throws an error, None is put in the dict for that feature.
        Print messages are shown only if extract.py is the main file.
        Returns:
            dict: All extracted features.
        """
        import sys
        
        is_main = sys.argv[0].endswith("extract.py")
        if is_main:
            logger.info("Starting Dynamic feature extraction...")
        features = {}
        feature_methods = [
            ("sparsity", self.getSparsity),
            ("locality_ratio", self.getQuantumLocalityRatio),
        ]
        is_main = sys.argv[0].endswith("extract.py")
        for key, method in feature_methods:
            try:
                result = method()
                # result is a dict with one key
                value = list(result.values())[0] if isinstance(result, dict) and result else None
                features[key] = value
                if is_main:
                    logger.debug(f"{key} feature completed.")
            except Exception as e:
                features[key] = None
                if is_main:
                    logger.warning(f"{key} feature failed: {e}")
        if is_main:
            logger.info("Done extracting Dynamic features.")
        return features
    

    