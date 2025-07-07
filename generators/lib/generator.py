from abc import ABC
from dataclasses import dataclass
from qiskit import QuantumCircuit


@dataclass
class BaseParams:
    max_qubits: int
    min_qubits: int
    max_depth: int
    min_depth: int
    min_reps: int = 1
    max_reps: int = 5
    min_eval_qubits: int = 2
    max_eval_qubits: int = 6
    measure: bool = False
    seed: int = None


class Generator(ABC):
    """
    Abstract base class for generators.
    """

    def __init__(self, base_params: BaseParams):
        """
        Initialize the generator with a configuration.

        :param config: Configuration dictionary for the generator.
        """
        self.base_params = base_params

    def generate(self, *args, **kwargs) -> QuantumCircuit | None:
        """
        Generate content based on the provided arguments.

        :param args: Positional arguments for generation.
        :param kwargs: Keyword arguments for generation.
        :return: Generated content.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def generate_parameters(self) -> tuple:
        """
        Generate parameters for the generator.

        :return: Parameters for the generator.
        """
        raise NotImplementedError("Subclasses must implement this method.")
