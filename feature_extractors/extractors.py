from feature_extractors.graph_features import GraphFeatureExtracter
from feature_extractors.static_features import StaticFeatureExtractor
from feature_extractors.dynamic_features import DynamicFeatureExtractor
from feature_extractors.static_features import FeatureExtracter
from qiskit import QuantumCircuit



def extract_features(circuit: QuantumCircuit):
    """
    Extracts static and graph features from a given quantum circuit.
    
    Args:
        circuit (QuantumCircuit): The quantum circuit to analyze.
    
    Returns:
        dict: A dictionary containing extracted features.
    """
    if not isinstance(circuit, QuantumCircuit):
        raise ValueError("Input must be a QuantumCircuit instance.")
    
    # Initialize feature extractors
    feature_extractor = FeatureExtracter(circuit=circuit)
    graph_feature_extractor = GraphFeatureExtracter(circuit=circuit, feature_extractor=feature_extractor)
    static_feature_extractor = StaticFeatureExtractor(circuit=circuit, feature_extractor=feature_extractor)
    dynamic_feature_extractor = DynamicFeatureExtractor(circuit=circuit, feature_extractor=feature_extractor)
    
    # Extract features
    features = static_feature_extractor.extractAllFeatures()
    features.update(graph_feature_extractor.extractAllFeatures())
    features.update(dynamic_feature_extractor.extractAllFeatures())
    
    return features