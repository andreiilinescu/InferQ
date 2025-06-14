from __future__ import annotations

"""Approximate / *inexact* Quantum Phase Estimation (QPE) generator
===================================================================
This generator mirrors the *exact* QPE implementation but allows you to
**deliberately approximate** the inverse Quantum Fourier Transform to trade
circuit depth for precision.  The approximation is controlled via
``approximation_degree`` – identical to the parameter used in
:class:`qiskit.circuit.library.QFT`.

Key idea
~~~~~~~~
Dropping controlled‑phase rotations smaller than ``π / 2**approximation_degree``
reduces two‑qubit gate count from *O(m²)* to *O(m log(1/ε))* while introducing a
bounded phase error ε.  For many NISQ use‑cases a modest
``approximation_degree ≈ 2–3`` dramatically lowers depth with only a few bits
of precision loss – hence **“inexact QPE”**.

Usage
-----
```python
from qiskit.circuit.library import RZ
from qpe_inexact import generate, demo_state_prep

phi = 0.34375   # 44/128
qc = generate(m=7, unitary=RZ(2*math.pi*phi), prepare_eigenstate=demo_state_prep(),
              approximation_degree=2)
print(qc.draw())
```

Parameters
~~~~~~~~~~
* ``m`` – evaluation‑qubit count.
* ``unitary`` – gate/circuit implementing *n‑qubit* U.
* ``prepare_eigenstate`` – circuit preparing an eigenstate |ψ⟩ of U.
* ``approximation_degree`` – non‑negative integer.  0 ⇒ exact QFT; 1 drops
  controlled‑phase of angle π/2; 2 drops π/4, etc.
* ``measure`` – attach measurements (default ``True``).
* ``name`` – custom circuit name.

Returns :class:`qiskit.circuit.QuantumCircuit` (m + n qubits).
"""

from typing import Optional

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Gate
from qiskit.circuit.library import QFT

# -----------------------------------------------------------------------------
# Demo helper – prepare |1⟩ for single‑qubit Z‑family gates
# -----------------------------------------------------------------------------


def demo_state_prep() -> QuantumCircuit:
    qc = QuantumCircuit(1, name="|1⟩ prep")
    qc.x(0)
    return qc


# -----------------------------------------------------------------------------
# Internal utilities
# -----------------------------------------------------------------------------


def _as_gate(obj) -> Gate:
    if isinstance(obj, Gate):
        return obj
    if isinstance(obj, QuantumCircuit):
        return obj.to_gate()
    raise TypeError("unitary must be Gate or QuantumCircuit")


def _controlled_power(U: Gate, power: int) -> Gate:
    return U.power(power).control(1)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def generate(
    *,
    m: int,
    unitary,
    prepare_eigenstate: QuantumCircuit,
    approximation_degree: int = 1,
    measure: bool = True,
    name: Optional[str] = None,
) -> QuantumCircuit:
    """Build an *approximate* QPE circuit with truncated inverse QFT."""

    if m < 1:
        raise ValueError("m must be ≥ 1")
    if approximation_degree < 0:
        raise ValueError("approximation_degree must be ≥ 0")

    U_gate = _as_gate(unitary)
    n_sys = prepare_eigenstate.num_qubits
    if U_gate.num_qubits != n_sys:
        raise ValueError("unitary and eigenstate prep must act on same #qubits")

    # Registers
    qr_eval = QuantumRegister(m, "qpe")
    qr_sys = QuantumRegister(n_sys, "sys")
    cr_eval = ClassicalRegister(m, "c") if measure else None
    qc = (
        QuantumCircuit(qr_eval, qr_sys, cr_eval)
        if cr_eval
        else QuantumCircuit(qr_eval, qr_sys)
    )
    qc.name = name or f"QPE_inexact_deg{approximation_degree}"

    # 1) Eigenstate preparation
    qc.append(prepare_eigenstate.to_gate(label="Prep|ψ⟩"), qr_sys)

    # 2) Hadamard layer
    qc.h(qr_eval)

    # 3) Controlled‑powers of U
    for j in range(m):
        power = 2**j
        qc.append(_controlled_power(U_gate, power), [qr_eval[j], *qr_sys])

    # 4) Approximate inverse QFT
    qft_inv = QFT(
        num_qubits=m,
        approximation_degree=approximation_degree,
        inverse=True,
        do_swaps=False,
        name="QFT†~",
    )
    qc.append(qft_inv, qr_eval)

    # 5) Measurement
    if measure:
        qc.barrier()
        qc.measure(qr_eval, cr_eval)  # type: ignore[arg-type]

    qc.metadata = {
        "algorithm": "InexactQPE",
        "m_eval": m,
        "n_system": n_sys,
        "approx_deg": approximation_degree,
        "measured": measure,
    }
    return qc


# -----------------------------------------------------------------------------
# CLI helper -------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import argparse, math
    from qiskit.circuit.library import RZ
    from qiskit.visualization import circuit_drawer

    parser = argparse.ArgumentParser(
        description="Generate an inexact QPE circuit and save SVG."
    )
    parser.add_argument("m", type=int, help="Evaluation qubits")
    parser.add_argument(
        "--phi", type=float, default=0.34375, help="Eigen‑phase φ in [0,1)"
    )
    parser.add_argument("--deg", type=int, default=1, help="Approximation degree (≥0)")
    parser.add_argument("--outfile", default="qpe_inexact.svg", help="Output filename")
    args = parser.parse_args()

    U_demo = RZ(2 * math.pi * args.phi)
    qc_cli = generate(
        m=args.m,
        unitary=U_demo,
        prepare_eigenstate=demo_state_prep(),
        approximation_degree=args.deg,
    )
    circuit_drawer(qc_cli, output="mpl", filename=args.outfile, style="iqp")
    print(f"Saved to {args.outfile}")
