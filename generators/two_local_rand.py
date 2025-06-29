# Import necessary Qiskit components
from qiskit.circuit.library import TwoLocal
from qiskit.circuit import QuantumCircuit, ParameterVector
import numpy as np # Import numpy for generating random numbers

def create_two_local_circuit(
    num_qubits: int,
    reps: int,
    rotation_blocks: list[str] = None,
    entanglement_blocks: list[str] = None,
    entanglement: str = 'full',
    skip_final_rotation_layer: bool = False
) -> QuantumCircuit:
    """
    Creates a TwoLocal variational form as a Qiskit QuantumCircuit.

    The TwoLocal circuit is a flexible ansatz that allows for customization
    of its rotation and entanglement blocks. It's composed of alternating
    layers of chosen rotation gates and chosen entanglement gates.

    Args:
        num_qubits (int): The number of qubits in the circuit.
        reps (int): The number of repetitions (layers) of the ansatz.
        rotation_blocks (list[str], optional): A list of gate names (e.g., ['ry', 'rz'])
                                               to use for the rotation layers.
                                               Defaults to ['ry', 'rz'] if None.
        entanglement_blocks (list[str], optional): A list of gate names (e.g., ['cx'])
                                                  to use for the entanglement layers.
                                                  Defaults to ['cx'] if None.
        entanglement (str): Specifies the entanglement pattern. Common options include
                            'full', 'linear', 'circular', or a list of qubit pairs.
                            Defaults to 'full'.
        skip_final_rotation_layer (bool): If True, the last rotation layer is omitted.
                                          Defaults to False.

    Returns:
        QuantumCircuit: A Qiskit QuantumCircuit representing the TwoLocal ansatz.
                        The circuit's parameters are exposed as `Parameter` objects.
    """
    if rotation_blocks is None:
        rotation_blocks = ['ry', 'rz']
    if entanglement_blocks is None:
        entanglement_blocks = ['cx']

    # Initialize the TwoLocal circuit.
    # TwoLocal automatically creates its own parameters based on the chosen blocks and reps.
    ansatz = TwoLocal(
        num_qubits=num_qubits,
        reps=reps,
        rotation_blocks=rotation_blocks,
        entanglement_blocks=entanglement_blocks,
        entanglement=entanglement,
        skip_final_rotation_layer=skip_final_rotation_layer
    )

    return ansatz

def generate(
    num_qubits: int,
    reps: int,
    parameter_values: list[float],
    rotation_blocks: list[str] = None,
    entanglement_blocks: list[str] = None,
    entanglement: str = 'full',
    skip_final_rotation_layer: bool = False
) -> QuantumCircuit:
    """
    Creates and completes a TwoLocal Qiskit circuit with the provided parameters.

    This function first builds the parameterized TwoLocal circuit structure
    and then assigns the given numerical parameter values to it, resulting
    in a fully defined quantum circuit.

    Args:
        num_qubits (int): The number of qubits in the circuit.
        reps (int): The number of repetitions (layers) of the ansatz.
        parameter_values (list[float]): A list of numerical values to bind to the
                                        circuit's parameters. The length of this list
                                        must match the number of parameters expected
                                        by the TwoLocal circuit.
        rotation_blocks (list[str], optional): A list of gate names (e.g., ['ry', 'rz'])
                                               to use for the rotation layers.
                                               Defaults to ['ry', 'rz'] if None.
        entanglement_blocks (list[str], optional): A list of gate names (e.g., ['cx'])
                                                  to use for the entanglement layers.
                                                  Defaults to ['cx'] if None.
        entanglement (str): Specifies the entanglement pattern. Common options include
                            'full', 'linear', 'circular', or a list of qubit pairs.
                            Defaults to 'full'.
        skip_final_rotation_layer (bool): If True, the last rotation layer is omitted.
                                          Defaults to False.

    Returns:
        QuantumCircuit: A Qiskit QuantumCircuit with all its parameters bound to
                        the provided numerical values. Returns None if parameter
                        count does not match.
    """
    # CBasic Two local Circuti created. 
    ansatz = create_two_local_circuit(
        num_qubits=num_qubits,
        reps=reps,
        rotation_blocks=rotation_blocks,
        entanglement_blocks=entanglement_blocks,
        entanglement=entanglement,
        skip_final_rotation_layer=skip_final_rotation_layer
    )

    # Check if the provided parameter_values match the number of expected parameters
    expected_params = len(ansatz.parameters)
    if len(parameter_values) != expected_params:
        print(f"Error: Mismatch in parameter count. Expected {expected_params} parameters, "
              f"but got {len(parameter_values)} values.")
        return None # Return None or raise an error if the counts don't match

    # Assign the numerical values to the parameters
    completed_circuit = ansatz.assign_parameters(parameter_values)
    return completed_circuit
