from __future__ import annotations
from typing import Optional

from qiskit import QuantumCircuit
from qiskit.circuit.library import (
    ZFeatureMap,
    ZZFeatureMap,
    PauliFeatureMap,
    RealAmplitudes,
    EfficientSU2,
    TwoLocal,
)
from generators.lib.generator import Generator, BaseParams
from generators.lib.parameters import (
    num_qbits,
    qnn_feature_map_type,
    qnn_ansatz_type,
    qnn_reps,
)

"""Quantum Neural Network (QNN) circuit generator
===============================================
This module provides both a class-based QNN generator and a functional interface
for generating Quantum Neural Network circuits. It supports various feature maps
(ZFeatureMap, ZZFeatureMap, PauliFeatureMap) and ansätze (RealAmplitudes, 
EfficientSU2, TwoLocal) with configurable repetitions and entanglement patterns.

Quick example
~~~~~~~~~~~~~
```python
# Class-based approach
from qnn import QNNGenerator
from generators.lib.generator import BaseParams

params = BaseParams(max_qubits=5, min_qubits=2, measure=True)
qnn_gen = QNNGenerator(params)
n, feature_map_type, ansatz_type, reps_num = qnn_gen.generate_parameters()
qc = qnn_gen.generate(n, feature_map_type, ansatz_type, reps_num)

# Function-based approach
from qnn import generate
qc = generate(n=4, feature_map='ZZFeatureMap', ansatz='RealAmplitudes', reps=2)
```

Parameters
~~~~~~~~~~
* ``n`` – number of qubits (``n ≥ 1``).
* ``feature_map`` – type of feature map ('ZFeatureMap', 'ZZFeatureMap', 'PauliFeatureMap').
* ``ansatz`` – type of ansatz ('RealAmplitudes', 'EfficientSU2', 'TwoLocal').
* ``reps`` – number of repetitions for the ansatz.
* ``entanglement`` – entanglement pattern for certain ansätze.
* ``measure`` – whether to add measurements. Default ``False``.
* ``name`` – optional circuit name.

Returns
~~~~~~~
:class:`qiskit.circuit.QuantumCircuit` containing the QNN circuit.
"""


class QNN(Generator):
    """
    Class to generate a Quantum Neural Network circuit.
    """

    def __init__(self, base_params: BaseParams):
        super().__init__(base_params)
        self.measure = self.base_params.measure

    def generate(
        self,
        num_qubits: int,
        feature_map_type: str = "ZZFeatureMap",
        ansatz_type: str = "RealAmplitudes",
        reps_num: int = 1,
        entanglement: Optional[str] = None,
        name: Optional[str] = None,
    ) -> QuantumCircuit:
        """
        Generate a Quantum Neural Network circuit.

        Args:
            num_qubits (int): Number of qubits (≥ 1).
            feature_map_type (str): Type of feature map.
            ansatz_type (str): Type of ansatz.
            reps_num (int): Number of repetitions for ansatz.
            entanglement (Optional[str]): Entanglement pattern.
            name (Optional[str]): Optional circuit name.

        Returns:
            QuantumCircuit: The generated QNN circuit.
        """
        if num_qubits < 1:
            raise ValueError("num_qubits must be ≥ 1")

        # Create the quantum circuit
        qc = QuantumCircuit(num_qubits)
        qc.name = name or f"QNN({num_qubits}q,{feature_map_type},{ansatz_type})"

        # Create feature map
        feature_map = self._create_feature_map(feature_map_type, num_qubits)
        qc.compose(feature_map, inplace=True)

        # Add barrier for visual separation
        qc.barrier()

        # Create ansatz
        ansatz = self._create_ansatz(ansatz_type, num_qubits, reps_num, entanglement)
        qc.compose(ansatz, inplace=True)

        # Add measurements if requested
        if self.measure:
            qc.barrier()
            qc.measure_all()

        # Metadata
        qc.metadata = {
            "algorithm": "QNN",
            "n_qubits": num_qubits,
            "feature_map": feature_map_type,
            "ansatz": ansatz_type,
            "reps": reps_num,
            "entanglement": entanglement,
            "measured": self.measure,
        }

        return qc

    def _create_feature_map(self, feature_map_type: str, num_qubits: int):
        """Create the specified feature map."""
        if feature_map_type == "ZFeatureMap":
            return ZFeatureMap(feature_dimension=num_qubits, reps=1)
        elif feature_map_type == "ZZFeatureMap":
            return ZZFeatureMap(feature_dimension=num_qubits, reps=1)
        elif feature_map_type == "PauliFeatureMap":
            return PauliFeatureMap(feature_dimension=num_qubits, reps=1)
        else:
            raise ValueError(f"Unknown feature map type: {feature_map_type}")

    def _create_ansatz(
        self,
        ansatz_type: str,
        num_qubits: int,
        reps_num: int,
        entanglement: Optional[str],
    ):
        """Create the specified ansatz."""
        # Set default entanglement if not specified
        if entanglement is None:
            entanglement = "linear"

        if ansatz_type == "RealAmplitudes":
            return RealAmplitudes(
                num_qubits=num_qubits, reps=reps_num, entanglement=entanglement
            )
        elif ansatz_type == "EfficientSU2":
            return EfficientSU2(
                num_qubits=num_qubits, reps=reps_num, entanglement=entanglement
            )
        elif ansatz_type == "TwoLocal":
            return TwoLocal(
                num_qubits=num_qubits,
                rotation_blocks="ry",
                entanglement_blocks="cx",
                entanglement=entanglement,
                reps=reps_num,
            )
        else:
            raise ValueError(f"Unknown ansatz type: {ansatz_type}")

    def generate_parameters(self) -> tuple[int, str, str, int]:
        """
        Generate parameters for the QNN circuit.

        Returns:
            tuple: (num_qubits, feature_map_type, ansatz_type, reps_num)
        """
        self.num_qubits = num_qbits(
            self.base_params.min_qubits,
            self.base_params.max_qubits,
            self.base_params.seed,
        )

        # Generate feature map type using parameter helper
        self.feature_map_type = qnn_feature_map_type(self.base_params.seed)

        # Generate ansatz type using parameter helper
        self.ansatz_type = qnn_ansatz_type(self.base_params.seed)

        # Generate number of repetitions using parameter helper
        self.reps_num = qnn_reps(self.base_params.seed, 1, 3)

        return self.num_qubits, self.feature_map_type, self.ansatz_type, self.reps_num


# -----------------------------------------------------------------------------
# Public API (backward compatibility)
# -----------------------------------------------------------------------------


def generate(
    n: int,
    feature_map: str = "ZZFeatureMap",
    ansatz: str = "RealAmplitudes",
    reps_num: int = 1,
    entanglement: Optional[str] = None,
    measure: bool = False,
    name: Optional[str] = None,
) -> QuantumCircuit:
    """
    Generate a Quantum Neural Network circuit (functional interface).

    Args:
        n (int): Number of qubits.
        feature_map (str): Type of feature map.
        ansatz (str): Type of ansatz.
        reps_num (int): Number of repetitions.
        entanglement (Optional[str]): Entanglement pattern.
        measure (bool): Whether to add measurements.
        name (Optional[str]): Circuit name.

    Returns:
        QuantumCircuit: The generated QNN circuit.
    """
    # Create a temporary BaseParams for the generator
    from generators.lib.generator import BaseParams

    params = BaseParams(
        max_qubits=n, min_qubits=n, max_depth=1, min_depth=1, measure=measure, seed=None
    )

    qnn_gen = QNN(params)
    return qnn_gen.generate(n, feature_map, ansatz, reps_num, entanglement, name)


# -----------------------------------------------------------------------------
# CLI for quick visualization
# -----------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import argparse
    from qiskit.visualization import circuit_drawer

    parser = argparse.ArgumentParser(
        description="Generate a QNN circuit and save to SVG."
    )
    parser.add_argument("n", type=int, help="Number of qubits (≥1)")
    parser.add_argument(
        "--feature-map",
        choices=["ZFeatureMap", "ZZFeatureMap", "PauliFeatureMap"],
        default="ZZFeatureMap",
        help="Feature map type",
    )
    parser.add_argument(
        "--ansatz",
        choices=["RealAmplitudes", "EfficientSU2", "TwoLocal"],
        default="RealAmplitudes",
        help="Ansatz type",
    )
    parser.add_argument("--reps", type=int, default=1, help="Number of repetitions")
    parser.add_argument("--measure", action="store_true", help="Add measurements")
    parser.add_argument("--outfile", default="qnn.svg", help="Output SVG filename")
    args = parser.parse_args()

    qc_cli = generate(
        n=args.n,
        feature_map=args.feature_map,
        ansatz=args.ansatz,
        reps_num=args.reps,
        measure=args.measure,
    )

    circuit_drawer(qc_cli, output="mpl", filename=args.outfile, style="iqp")
    print(f"Circuit saved to {args.outfile}")

    # Example usage of class-based approach
    print("\nExample using QNNGenerator class:")
    from generators.lib.generator import BaseParams

    params = BaseParams(
        max_qubits=args.n,
        min_qubits=args.n,
        max_depth=1,
        min_depth=1,
        measure=args.measure,
        seed=42,
    )

    qnn_gen = QNN(params)
    num_qubits, feature_map_type, ansatz_type, reps_num = qnn_gen.generate_parameters()
    qc_class = qnn_gen.generate(num_qubits, feature_map_type, ansatz_type, reps_num)
    print(
        f"Generated circuit: {qc_class.name}, qubits={qc_class.num_qubits}, depth={qc_class.depth()}"
    )
    print(
        f"Parameters: n={num_qubits}, feature_map={feature_map_type}, ansatz={ansatz_type}, reps={reps_num}"
    )
