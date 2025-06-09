from qiskit.circuit.library import RealAmplitudes
from qiskit.circuit import QuantumCircuit, ParameterVector
import numpy as np 

def create_real_amplitudes_circuit(num_qubits: int, depth: int) -> QuantumCircuit:
    """
    Creates a RealAmplitudes variational form as a Qiskit QuantumCircuit.

    The RealAmplitudes circuit is a hardware-efficient ansatz commonly used
    in variational quantum algorithms (VQAs). It consists of alternating layers
    of Y-rotations (Ry gates) and entangling blocks (typically CNOTs or RZCNOTs).

    Args:
        num_qubits (int): The number of qubits in the circuit.
        depth (int): The number of layers (repetitions) of the ansatz.
                     Each layer consists of Ry gates followed by an entangling block.

    Returns:
        QuantumCircuit: A Qiskit QuantumCircuit representing the RealAmplitudes ansatz.
                        The circuit's parameters are exposed as `Parameter` objects,
                        allowing them to be bound later.
    """
    # Initialize the RealAmplitudes circuit.
    # By default, RealAmplitudes creates its own parameters.
    ansatz = RealAmplitudes(num_qubits=num_qubits, reps=depth)

    return ansatz

def get_completed_real_amplitudes_circuit(num_qubits: int, depth: int, parameter_values: list[float]) -> QuantumCircuit:
    """
    Creates and completes a RealAmplitudes Qiskit circuit with the provided parameters.

    This function first builds the parameterized RealAmplitudes circuit structure
    and then assigns the given numerical parameter values to it, resulting
    in a fully defined quantum circuit.

    Args:
        num_qubits (int): The number of qubits in the circuit.
        depth (int): The number of layers (repetitions) of the ansatz.
        parameter_values (list[float]): A list of numerical values to bind to the
                                        circuit's parameters. The length of this list
                                        must match the number of parameters expected
                                        by the RealAmplitudes circuit (num_qubits * (depth + 1)).

    Returns:
        QuantumCircuit: A Qiskit QuantumCircuit with all its parameters bound to
                        the provided numerical values. Returns None if parameter
                        count does not match.
    """
    #Create the base parameterized RealAmplitudes circuit usign Qiskit API Circuits
    ansatzCircuit = create_real_amplitudes_circuit(num_qubits=num_qubits, depth=depth)

    # Check if the provided parameter_values match the number of expected parameters
    expected_params = len(ansatzCircuit.parameters)
    if len(parameter_values) != expected_params:
        print(f"Error: Mismatch in parameter count. Expected {expected_params} parameters, "
              f"but got {len(parameter_values)} values.")
        return None # Return None or raise an error if the counts don't match

    # Assign the numerical values to the parameters
    completed_circuit = ansatzCircuit.assign_parameters(parameter_values)
    return completed_circuit

