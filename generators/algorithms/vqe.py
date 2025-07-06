from __future__ import annotations
from typing import Tuple, List, Optional, Union

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Parameter
from qiskit.circuit.library import (
    RealAmplitudes,
    EfficientSU2,
    TwoLocal,
    NLocal,
)

from generators.lib.generator import Generator, BaseParams
from generators.lib.parameters import (
    num_qbits,
    vqe_ansatz_type,
    vqe_reps,
    vqe_entanglement_pattern,
    vqe_parameter_prefix,
)

"""Variational Quantum Eigensolver (VQE) circuit generator
=========================================================
This module offers a single public entry‑point :pyfunc:`generate` that returns a
**parameterised ansatz circuit** suitable for use in a VQE workflow.  While the
full VQE algorithm requires generating *measurement* circuits for each Pauli
term of the Hamiltonian, that outer loop is optimiser‑specific; here we focus
on building the *ansatz* (trial wave‑function) with sensible defaults and
metadata.

Features
~~~~~~~~
* Choose one of Qiskit’s standard ansatz templates
  (``"real_amplitudes"``, ``"efficient_su2"``, ``"two_local"``, ``"su2"``) **or**
  pass your own :class:`~qiskit.circuit.QuantumCircuit`.
* Control depth via ``reps`` and entanglement pattern via ``entanglement``.
* Optionally embed measurement gates so the circuit is executable as‑is.

Example – 6‑qubit RealAmplitudes ansatz
--------------------------------------
```python
from vqe import generate
qc, params = generate(n=6, ansatz="real_amplitudes", reps=2)
print(qc.draw())
```

API
~~~
```python
vqe.generate(
    *,
    n: int,                        # number of qubits
    ansatz: str | QuantumCircuit = "real_amplitudes",
    reps: int = 1,
    entanglement: str | list[str] = "full",
    parameter_prefix: str = "θ",
    measure: bool = True,
    name: str | None = None,
) -> tuple[QuantumCircuit, list[Parameter]]
```
The function returns the **ansatz circuit** (with optional measurements) and
its ordered list of :class:`~qiskit.circuit.Parameter` objects so you can plug
values into an optimiser.
"""


# Mapping from string → ansatz class ------------------------------------------------
_ANSATZ_MAP = {
    "real_amplitudes": RealAmplitudes,
    "efficient_su2": EfficientSU2,
    "two_local": TwoLocal,
    "su2": EfficientSU2,  # alias
}


# -----------------------------------------------------------------------------
# Class-based VQE Generator
# -----------------------------------------------------------------------------


class VQEGenerator(Generator):
    """Class-based generator for Variational Quantum Eigensolver (VQE) ansatz circuits.

    This generator creates parameterized ansatz circuits suitable for VQE workflows.
    It supports various ansatz templates from Qiskit's circuit library and allows
    customization of depth, entanglement patterns, and parameter naming.

    Example:
        >>> from generators.lib.generator import BaseParams
        >>> params = BaseParams(max_qubits=5, min_qubits=2, measure=True)
        >>> generator = VQEGenerator(params)
        >>> vqe_params = generator.generate_parameters()
        >>> qc, circuit_params = generator.generate(vqe_params['n'], **vqe_params)
        >>> print(f"Generated VQE circuit with {len(circuit_params)} parameters")
    """

    def __init__(self, base_params: BaseParams):
        super().__init__(base_params)
        self.measure = self.base_params.measure

    def generate(
        self,
        n: int,
        ansatz: Union[str, QuantumCircuit] = "real_amplitudes",
        reps: int = 1,
        entanglement: Union[str, List[str]] = "full",
        parameter_prefix: str = "θ",
        measure: Optional[bool] = None,
        name: Optional[str] = None,
    ) -> Tuple[QuantumCircuit, List[Parameter]]:
        """Generate a VQE ansatz circuit.

        Args:
            n: Number of qubits.
            ansatz: Either a string key (see docs) or a pre-built QuantumCircuit.
            reps: Number of repeated layers in the ansatz template.
            entanglement: Entanglement pattern for the ansatz.
            parameter_prefix: Prefix for automatic Parameter symbol names.
            measure: If True, append measurement gates. If None, uses base_params.measure.
            name: Optional circuit name.

        Returns:
            Tuple of (QuantumCircuit, list of Parameters).
        """
        if measure is None:
            measure = self.measure

        return generate(
            n=n,
            ansatz=ansatz,
            reps=reps,
            entanglement=entanglement,
            parameter_prefix=parameter_prefix,
            measure=measure,
            name=name,
        )

    def generate_parameters(self) -> dict:
        """Generate parameters for the VQE circuit using base_params.

        Returns:
            Dictionary containing all parameters needed for generate().
        """
        self.num_qubits = num_qbits(
            self.base_params.min_qubits,
            self.base_params.max_qubits,
            self.base_params.seed,
        )
        self.ansatz = vqe_ansatz_type(seed=self.base_params.seed)
        self.reps = vqe_reps(seed=self.base_params.seed)
        self.entanglement = vqe_entanglement_pattern(seed=self.base_params.seed)
        self.parameter_prefix = vqe_parameter_prefix(seed=self.base_params.seed)
        self.measure = self.base_params.measure

        return {
            "n": self.num_qubits,
            "ansatz": self.ansatz,
            "reps": self.reps,
            "entanglement": self.entanglement,
            "parameter_prefix": self.parameter_prefix,
            "measure": self.measure,
            "name": f"VQE_{self.ansatz}_{self.num_qubits}q",
        }


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def generate(
    *,
    n: int,
    ansatz: Union[str, QuantumCircuit] = "real_amplitudes",
    reps: int = 1,
    entanglement: Union[str, List[str]] = "full",
    parameter_prefix: str = "θ",
    measure: bool = True,
    name: Optional[str] = None,
) -> Tuple[QuantumCircuit, List[Parameter]]:  # noqa: D401
    """Build and return a parameterised ansatz circuit for VQE.

    Parameters
    ----------
    n
        Number of qubits.
    ansatz
        Either a string key (see docs) or a pre‑built QuantumCircuit.
    reps
        Number of repeated layers in the ansatz template (ignored if
        ``ansatz`` is a circuit).
    entanglement
        Entanglement pattern recognised by Qiskit templates (``"full"``,
        ``"linear"``, ``"circular"`` …) or explicit list of cNOT pairs.
    parameter_prefix
        Prefix for automatic :class:`Parameter` symbol names.
    measure
        If ``True`` append an ``n``‑bit classical register and measure all
        qubits so the circuit is runnable on hardware.
    name
        Optional circuit name.

    Returns
    -------
    (QuantumCircuit, list[Parameter])
        The ansatz circuit plus *ordered* list of its parameters.
    """

    if n < 1:
        raise ValueError("n must be ≥ 1")
    if reps < 1:
        raise ValueError("reps must be ≥ 1")

    # ------------------------------------------------------------------
    # Build / validate ansatz template
    # ------------------------------------------------------------------
    if isinstance(ansatz, QuantumCircuit):
        template: QuantumCircuit = ansatz
    else:
        key = ansatz.lower()
        if key not in _ANSATZ_MAP:
            raise ValueError(
                f"Unknown ansatz '{ansatz}'. Choose from {list(_ANSATZ_MAP)} or supply a circuit."
            )
        cls = _ANSATZ_MAP[key]
        if issubclass(cls, NLocal):
            template = cls(
                num_qubits=n,
                reps=reps,
                entanglement=entanglement,
                parameter_prefix=parameter_prefix,
            )
        else:  # pragma: no cover – all mapped classes are NLocal
            template = cls(
                num_qubits=n,
                reps=reps,
                entanglement=entanglement,
                parameter_prefix=parameter_prefix,
            )

    params: List[Parameter] = list(template.parameters)

    # ------------------------------------------------------------------
    # Wrap into outer circuit with measurement (optional)
    # ------------------------------------------------------------------
    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n, "c") if measure else None
    qc = QuantumCircuit(qr, cr) if cr else QuantumCircuit(qr)
    qc.name = name or f"VQE_{template.name}"  # type: ignore[attr-defined]

    qc.append(template.to_gate(label=template.name), qr)

    if measure:
        qc.barrier()
        qc.measure(qr, cr)  # type: ignore[arg-type]

    qc.metadata = {
        "algorithm": "VQE_ansatz",
        "n_qubits": n,
        "ansatz": template.name,  # type: ignore[attr-defined]
        "reps": reps,
        "entanglement": entanglement,
        "param_count": len(params),
        "measured": measure,
    }

    return qc, params


# -----------------------------------------------------------------------------
# CLI helper
# -----------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    from generators.lib.generator import BaseParams

    # Example usage following GHZ pattern
    params = BaseParams(
        max_qubits=6, min_qubits=2, max_depth=10, min_depth=1, measure=True, seed=42
    )
    vqe_generator = VQEGenerator(params)
    vqe_params = vqe_generator.generate_parameters()
    vqe_circuit, circuit_params = vqe_generator.generate(**vqe_params)

    print("VQE Circuit Generated:")
    print(f"Name: {vqe_circuit.name}")
    print(f"Qubits: {vqe_params['n']}")
    print(f"Ansatz: {vqe_params['ansatz']}")
    print(f"Reps: {vqe_params['reps']}")
    print(f"Parameters: {len(circuit_params)}")
    print(f"Metadata: {vqe_circuit.metadata}")
    print(vqe_circuit)


# -----------------------------------------------------------------------------
# Usage Examples
# -----------------------------------------------------------------------------


def demo_usage():  # pragma: no cover
    """Demonstrate both class-based and function-based VQE usage."""
    from generators.lib.generator import BaseParams

    print("=== VQE Generator Examples ===\n")

    # Class-based usage (following GHZ pattern)
    print("1. Class-based usage with BaseParams:")
    params = BaseParams(max_qubits=4, min_qubits=2, measure=True, seed=123)
    generator = VQEGenerator(params)
    vqe_params = generator.generate_parameters()
    qc, circuit_params = generator.generate(**vqe_params)
    print(f"   Generated: {qc.name}")
    print(f"   Qubits: {vqe_params['n']}, Ansatz: {vqe_params['ansatz']}")
    print(f"   Circuit Parameters: {len(circuit_params)}")
    print()

    # Function-based usage
    print("2. Function-based usage:")
    qc, circuit_params = generate(n=3, ansatz="efficient_su2", reps=1)
    print(f"   Generated: {qc.name}")
    print(f"   Circuit Parameters: {len(circuit_params)}")
    print()


# Backward compatibility: keep generate_random for existing code
def generate_random(
    n: int,
    seed: Optional[int] = None,
    measure: bool = True,
    name: Optional[str] = None,
) -> Tuple[QuantumCircuit, List[Parameter]]:
    """Generate a VQE circuit with random parameters (backward compatibility).

    Args:
        n: Number of qubits.
        seed: Random seed for reproducibility.
        measure: If True, append measurement gates.
        name: Optional circuit name.

    Returns:
        Tuple of (QuantumCircuit, list of Parameters).
    """
    ansatz = vqe_ansatz_type(seed=seed)
    reps = vqe_reps(seed=seed)
    entanglement = vqe_entanglement_pattern(seed=seed)
    parameter_prefix = vqe_parameter_prefix(seed=seed)

    return generate(
        n=n,
        ansatz=ansatz,
        reps=reps,
        entanglement=entanglement,
        parameter_prefix=parameter_prefix,
        measure=measure,
        name=name or f"VQE_random_{ansatz}",
    )
