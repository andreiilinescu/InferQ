from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import real_amplitudes, z_feature_map

def generate(n: int) -> QuantumCircuit:
    """Returns a quantum circuit implementing a Quantum Neural Network (QNN) with a ZZ FeatureMap and a RealAmplitudes ansatz.

    Arguments:
        num_qubits: number of qubits of the returned quantum circuit
    """
    feature_map = z_feature_map(feature_dimension=n)
    ansatz = real_amplitudes(num_qubits=n, reps=1)
    qc = QuantumCircuit(n)
    qc.compose(feature_map, inplace=True)
    qc.compose(ansatz, inplace=True)
    qc.name = "qnn"
    return qc