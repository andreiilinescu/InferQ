from __future__ import annotations

"""Entangled Quantum Fourier Transform (QFT) circuit generator
==============================================================
This module adds an "entangled" twist to the vanilla QFT: it prepares **Bell‑
style entanglement** between two *n‑qubit* registers and then applies the QFT
(or its inverse) to the *first* register.  The resulting circuit is useful for
pedagogical demonstrations showing how QFT acts on half of an entangled pair
and for protocols like *quantum teleportation of rotations*.

Quick demo
~~~~~~~~~~
```python
from qft_entangled import generate
qc = generate(n=3)  # forward QFT with swaps + measurement on both regs
qc.draw("mpl")
```

Parameters
~~~~~~~~~~
* ``n`` – number of qubits per register (``n ≥ 1``).
* ``inverse`` – build inverse‑QFT instead of forward (default ``False``).
* ``do_swaps`` – include qubit‑reversal swaps inside the QFT (default ``True``).
* ``measure`` – add ``2n``‑bit classical register measuring *both* registers
  (default ``True``).
* ``entangle`` – if ``True`` create Bell pairs via *H + CX* on each qubit pair
  before the QFT; if ``False`` the two registers start in |0…0⟩ (default
  ``True``).
* ``name`` – optional custom circuit name.

Return value is a :class:`qiskit.circuit.QuantumCircuit` containing two quantum
registers labelled ``src`` (where QFT is applied) and ``tgt`` (entangled copy).
"""

from typing import Optional

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import QFT

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def generate(
    *,
    n: int,
    inverse: bool = False,
    do_swaps: bool = True,
    measure: bool = False,
    entangle: bool = True,
    name: Optional[str] = None,
) -> QuantumCircuit:  # noqa: D401
    """Construct an entangled‑QFT circuit."""

    if n < 1:
        raise ValueError("n must be ≥ 1")

    src = QuantumRegister(n, "src")  # register that will undergo QFT
    tgt = QuantumRegister(n, "tgt")  # entangled partner register
    creg = ClassicalRegister(2 * n, "c") if measure else None

    qc = QuantumCircuit(src, tgt, creg) if creg else QuantumCircuit(src, tgt)
    qc.name = name or ("InvQFT_entangled" if inverse else "QFT_entangled")

    # --- entanglement -------------------------------------------------
    if entangle:
        qc.h(src)          # put |src⟩ in equal superposition
        for i in range(n):
            qc.cx(src[i], tgt[i])
    else:
        # Optionally start in |+⟩_src without entanglement
        qc.h(src)

    # --- apply QFT to src ---------------------------------------------
    qft_gate = QFT(n, inverse=inverse, do_swaps=do_swaps, name="QFT†" if inverse else "QFT")
    qc.append(qft_gate, src)

    if measure:
        qc.barrier()
        qc.measure(src, creg[:n])         # type: ignore[arg-type]
        qc.measure(tgt, creg[n:])         # type: ignore[arg-type]

    qc.metadata = {
        "algorithm": "EntangledQFT" if not inverse else "EntangledInverseQFT",
        "n_qubits_per_reg": n,
        "inverse": inverse,
        "do_swaps": do_swaps,
        "entangled": entangle,
        "measured": measure,
    }
    return qc


# -----------------------------------------------------------------------------
# CLI helper
# -----------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import argparse
    from qiskit.visualization import circuit_drawer

    parser = argparse.ArgumentParser(description="Generate entangled QFT circuit and save SVG.")
    parser.add_argument("n", type=int, help="Qubits per register (≥1)")
    parser.add_argument("--inverse", action="store_true", help="Generate inverse QFT")
    parser.add_argument("--no-swaps", dest="do_swaps", action="store_false", help="Omit swap network")
    parser.add_argument("--no-measure", dest="measure", action="store_false", help="No measurements")
    parser.add_argument("--no-entangle", dest="entangle", action="store_false", help="Skip Bell‑pair entanglement")
    parser.add_argument("--outfile", default="qft_entangled.svg", help="Output SVG filename")
    args = parser.parse_args()

    qc_cli = generate(
        n=args.n,
        inverse=args.inverse,
        do_swaps=args.do_swaps,
        measure=args.measure,
        entangle=args.entangle,
    )
    circuit_drawer(qc_cli, output="mpl", filename=args.outfile, style="iqp")
    print(f"Circuit saved to {args.outfile}")
