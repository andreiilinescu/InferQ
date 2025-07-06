from abc import ABC
from dataclasses import dataclass


@dataclass
class BaseParams:
    max_qubits: int
    min_qubits: int
    max_depth: int
    min_depth: int
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

    def generate(self, *args, **kwargs):
        """
        Generate content based on the provided arguments.

        :param args: Positional arguments for generation.
        :param kwargs: Keyword arguments for generation.
        :return: Generated content.
        """
        raise NotImplementedError("Subclasses must implement this method.")
