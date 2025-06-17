from __future__ import annotations

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

from typing import Tuple, List, Optional, Union

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Parameter
from qiskit.circuit.library import (
    RealAmplitudes,
    EfficientSU2,
    TwoLocal,
    NLocal,
)

# Mapping from string → ansatz class ------------------------------------------------
_ANSATZ_MAP = {
    "real_amplitudes": RealAmplitudes,
    "efficient_su2": EfficientSU2,
    "two_local": TwoLocal,
    "su2": EfficientSU2,  # alias
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
            raise ValueError(f"Unknown ansatz '{ansatz}'. Choose from {list(_ANSATZ_MAP)} or supply a circuit.")
        cls = _ANSATZ_MAP[key]
        if issubclass(cls, NLocal):
            template = cls(num_qubits=n, reps=reps, entanglement=entanglement, parameter_prefix=parameter_prefix)
        else:  # pragma: no cover – all mapped classes are NLocal
            template = cls(num_qubits=n, reps=reps, entanglement=entanglement, parameter_prefix=parameter_prefix)

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
    import argparse
    from qiskit.visualization import circuit_drawer

    parser = argparse.ArgumentParser(description="Generate VQE ansatz circuit and save SVG.")
    parser.add_argument("n", type=int, help="Number of qubits")
    parser.add_argument("--ansatz", default="real_amplitudes", help="Ansatz template name")
    parser.add_argument("--reps", type=int, default=1, help="Number of reps/layers")
    parser.add_argument("--outfile", default="vqe_ansatz.svg", help="Output SVG filename")
    args = parser.parse_args()

    qc_cli, _ = generate(n=args.n, ansatz=args.ansatz, reps=args.reps)
    circuit_drawer(qc_cli, output="mpl", filename=args.outfile, style="iqp")
    print(f"Circuit saved to {args.outfile}")
