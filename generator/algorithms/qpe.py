from qiskit.circuit.library import PhaseEstimation
from qiskit import QuantumCircuit
def create_phase_estimation_circuit(
    num_counting_qubits: int,
    unitary_operator: QuantumCircuit
) -> QuantumCircuit:
    """
    Creates a Quantum Phase Estimation (QPE) circuit.

    Args:
        num_counting_qubits (int): The number of qubits in the counting register.
                                   More qubits lead to higher precision.
        unitary_operator (QuantumCircuit): The unitary operator whose phase
                                           is to be estimated. This operator
                                           should act on the state register.

    Returns:
        QuantumCircuit: The Qiskit QuantumCircuit representing the QPE algorithm.
    """
    # The PhaseEstimation class automatically constructs the QPE circuit
    # It takes the number of counting qubits and the unitary operator.
    qpe_circuit = PhaseEstimation(
        num_counting_qubits=num_counting_qubits,
        unitary=unitary_operator
    )
    return qpe_circuit