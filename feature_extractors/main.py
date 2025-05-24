from qiskit import QuantumCircuit
from feature_extractors.static_features import static_features
from feature_extractors.graph_features import graph_features
from feature_extractors.dynamic_features import dynamic_features


def extract_all(circ: QuantumCircuit) -> dict:
    feats = {}
    for fn in (static_features, graph_features):
        feats.update(fn(circ))
    return feats
