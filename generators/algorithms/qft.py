from __future__ import annotations

"""Quantum Fourier Transform (QFT) circuit generator
====================================================
This module exposes a single public :pyfunc:`generate` function that produces a
Quantum Fourier Transform circuit using **Qiskit**'s built‑in
:class:`qiskit.circuit.library.QFT` template.  It supports both forward and
inverse transforms and optional qubit‑reversal swaps.

Quick example
~~~~~~~~~~~~~
```python
from qft import generate
qc = generate(n=5)              # 5‑qubit forward QFT with swaps + measurement
print(qc.draw())

qc_inv = generate(n=5, inverse=True, do_swaps=False)
```

Parameters
~~~~~~~~~~
* ``n`` – number of qubits (``n ≥ 1``).
* ``inverse`` – if ``True`` build the inverse QFT (*QFT†*). Default ``False``.
* ``do_swaps`` – include the canonical qubit‑reversal swaps. Default ``True``.
* ``measure`` – whether to add an ``n``‑bit classical register and measure all
  qubits. Default ``True``.
* ``name`` – optional circuit name.

Returns
~~~~~~~
:class:`qiskit.circuit.QuantumCircuit` containing the QFT (and optionally
measurements).
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
    name: Optional[str] = None,
) -> QuantumCircuit:  
    """Construct and return a QFT (or inverse QFT) circuit."""

    if n < 1:
        raise ValueError("n must be ≥ 1")

    qr = QuantumRegister(n, name="q")
    cr = ClassicalRegister(n, name="c") if measure else None

    qc = QuantumCircuit(qr, cr) if cr else QuantumCircuit(qr)
    qc.name = name or ("QFT†" if inverse else "QFT")

    # Append the QFT template
    qft_gate = QFT(num_qubits=n, approximation_degree=0, inverse=inverse, do_swaps=do_swaps, name="QFT†" if inverse else "QFT")
    qc.append(qft_gate, qr)

    if measure:
        qc.barrier()
        qc.measure(qr, cr)  # type: ignore[arg-type]

    # Metadata helpful for downstream tooling
    qc.metadata = {
        "algorithm": "QFT" if not inverse else "InverseQFT",
        "n_qubits": n,
        "inverse": inverse,
        "do_swaps": do_swaps,
        "measured": measure,
    }

    return qc


# -----------------------------------------------------------------------------
# CLI for quick visualization
# -----------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import argparse
    from qiskit.visualization import circuit_drawer

    parser = argparse.ArgumentParser(description="Generate a QFT circuit and save to SVG.")
    parser.add_argument("n", type=int, help="Number of qubits (≥1)")
    parser.add_argument("--inverse", action="store_true", help="Generate inverse QFT")
    parser.add_argument("--no‑swaps", dest="do_swaps", action="store_false", help="Omit final qubit‑reversal swaps")
    parser.add_argument("--no‑measure", dest="measure", action="store_false", help="Do not add measurements")
    parser.add_argument("--outfile", default="qft.svg", help="Output SVG filename")
    args = parser.parse_args()

    qc_cli = generate(n=args.n, inverse=args.inverse, do_swaps=args.do_swaps, measure=args.measure)
    circuit_drawer(qc_cli, output="mpl", filename=args.outfile, style="iqp")
    print(f"Circuit saved to {args.outfile}")
