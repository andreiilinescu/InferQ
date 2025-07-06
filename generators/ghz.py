from qiskit import QuantumCircuit
from generators.lib.generator import Generator, BaseParams
from generators.lib.parameters import num_qbits


class GHZ(Generator):
    """
    Class to generate a GHZ state circuit.
    """

    def __init__(self, base_params: BaseParams):
        super().__init__(base_params)

    def generate(self) -> QuantumCircuit:
        """
        Create an n-qubit GHZ state:
        |GHZ⟩ = (|0…0> + |1…1>)/√2
        """
        num_qbits = self.generate_parameters()
        qc = QuantumCircuit(num_qbits, name=f"GHZ({num_qbits})")
        qc.h(0)
        for i in range(num_qbits - 1):
            qc.cx(i, i + 1)

        if self.measure:
            qc.measure_all()

        return qc

    def generate_parameters(self) -> int:
        """
        Generate parameters for the GHZ circuit.
        """
        self.num_qubits = num_qbits(
            self.base_params.min_qubits,
            self.base_params.max_qubits,
            self.base_params.seed,
        )
        self.measure = self.base_params.measure
        return self.num_qubits


if __name__ == "__main__":
    # Example usage
    params = BaseParams(
        max_qubits=5, min_qubits=2, max_depth=10, min_depth=1, measure=False
    )
    ghz_generator = GHZ(params)
    ghz_circuit = ghz_generator.generate()
    print(ghz_circuit)
