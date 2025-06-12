from __future__ import annotations

"""Generic QAOA circuit generator (adjacency‑matrix + pluggable cost/mixer)
============================================================================
This module provides a single :pyfunc:`generate` entry‑point for building
Quantum Approximate Optimization Algorithm (QAOA) circuits **not just for
Max‑Cut but for *any* cost Hamiltonian**.  You can either supply an *adjacency
matrix* (for Max‑Cut) **or** pass in *callables* that append your own cost and
mixer layers.

Highlights
~~~~~~~~~~
* **Max‑Cut via adjacency matrix** – pass an ``n×n`` (weighted) symmetric matrix
  ``adjacency``; weight 0 means no edge.  The generator constructs the standard
  ZX‑sandwich cost unitary ``exp(-i γ w_{uv}(I-Z_u Z_v)/2)`` for each edge.
* **Fully custom problems** – provide ``cost_layer`` and optionally
  ``mixer_layer`` *callables* that will be invoked once per QAOA layer with
  signature ``layer(qc, qubits, angle)``.
* **Random or user‑supplied angles** – ``gammas`` and ``betas`` lists control
  the variational parameters; random values are filled in if omitted.

Example – Max‑Cut on a weighted square graph
-------------------------------------------
```python
from qaoa import generate
import numpy as np

adj = np.array([[0, 1, 0, 1],
                [1, 0, 1.2, 0],
                [0, 1.2, 0, 0.7],
                [1, 0, 0.7, 0]], dtype=float)

qc = generate(n=4, p=2, adjacency=adj)
qc.draw("mpl")
```

Example – Custom 1‑local cost H = Z₀ + 0.5 Z₁
---------------------------------------------
```python
from qiskit import QuantumCircuit
from qaoa import generate

def my_cost(qc: QuantumCircuit, q, gamma):
    # q is list of qubits (QuantumRegister)
    qc.rz(-2 * gamma, q[0])
    qc.rz(-gamma, q[1])

def my_mixer(qc: QuantumCircuit, q, beta):
    qc.rx(2 * beta, q)

qc = generate(n=2, p=3, cost_layer=my_cost, mixer_layer=my_mixer)
```

API
~~~
```python
qaoa.generate(
    *,
    n: int,                    # number of qubits
    p: int,                    # QAOA depth (≥1)
    adjacency: np.ndarray | list[list[float]] | None = None,
    cost_layer: callable | None = None,
    mixer_layer: callable | None = None,
    gammas: Sequence[float] | None = None,
    betas: Sequence[float]  | None = None,
    name: str | None = None,
) -> QuantumCircuit
```
Exactly **one** of ``adjacency`` XOR ``cost_layer`` must be supplied.
"""

from typing import Sequence, Callable, Optional, List
import random
import math
import numbers

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

# -----------------------------------------------------------------------------
# Helper – Max‑Cut two‑qubit cost evolution  e^{-i γ w (I - Z Z)/2}
# -----------------------------------------------------------------------------

def _maxcut_edge_unitary(qc: QuantumCircuit, u, v, gamma_weighted: float):
    qc.cx(u, v)
    qc.rz(-2 * gamma_weighted, v)  # phase = -2γw  (global phase ignored)
    qc.cx(u, v)


def _default_rx_mixer(qc: QuantumCircuit, qubits, beta: float):
    qc.rx(2 * beta, qubits)


# -----------------------------------------------------------------------------
# Public generator
# -----------------------------------------------------------------------------

def generate(
    *,
    n: int,
    p: int,
    adjacency: "np.ndarray | list[list[float]] | None" = None,
    cost_layer: "Callable[[QuantumCircuit, list, float], None] | None" = None,
    mixer_layer: "Callable[[QuantumCircuit, list, float], None] | None" = None,
    gammas: Sequence[float] | None = None,
    betas: Sequence[float] | None = None,
    name: Optional[str] = None,
    measure: bool = False,
) -> QuantumCircuit:
    """Return a QAOA circuit supporting Max‑Cut *or* arbitrary cost layers.

    *If* ``adjacency`` is given the problem is assumed to be Max‑Cut.
    Otherwise supply a ``cost_layer`` callable.  ``mixer_layer`` defaults to the
    RX mixer.
    """

    # --- validation -------------------------------------------------
    if n < 2:
        raise ValueError("n must be ≥ 2")
    if p < 1:
        raise ValueError("p must be ≥ 1")

    if (adjacency is None) == (cost_layer is None):
        raise ValueError("Exactly one of adjacency or cost_layer must be provided")

    if adjacency is not None:
        # Convert to ndarray and sanity‑check size & symmetry
        adj = np.asarray(adjacency, dtype=float)
        if adj.shape != (n, n):
            raise ValueError("adjacency must be an n×n matrix")
        if not np.allclose(adj, adj.T):
            raise ValueError("adjacency matrix must be symmetric (undirected graph)")
        # Pre‑extract weighted edges (u < v, weight ≠ 0)
        edges: List[tuple[int, int, float]] = [
            (u, v, adj[u, v]) for u in range(n) for v in range(u + 1, n) if adj[u, v] != 0
        ]
        if not edges:
            raise ValueError("Graph has no edges – nothing to optimise")

        def cost_layer(qc: QuantumCircuit, qubits, gamma):  # type: ignore[redefined-outer-name]
            for u, v, w in edges:
                _maxcut_edge_unitary(qc, qubits[u], qubits[v], gamma * w)

    mixer_layer = mixer_layer or _default_rx_mixer

    # --- parameter handling ----------------------------------------
    if gammas is None:
        gammas = [random.uniform(0, math.pi) for _ in range(p)]
    if betas is None:
        betas = [random.uniform(0, math.pi) for _ in range(p)]
    if len(gammas) != p or len(betas) != p:
        raise ValueError("gammas and betas must have length p")

    # --- circuit ----------------------------------------------------
    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n, "c")
    qc = QuantumCircuit(qr, cr, name=name or "QAOA")

    # Initial |+⟩ state
    qc.h(qr)

    # Layers ---------------------------------------------------------
    for layer in range(p):
        gamma = gammas[layer]
        beta = betas[layer]
        cost_layer(qc, qr, gamma)   # type: ignore[arg-type]
        mixer_layer(qc, qr, beta)   # type: ignore[arg-type]

    if measure:
        qc.barrier()
        qc.measure(qr, cr)

    qc.metadata = {
        "algorithm": "QAOA",
        "n_qubits": n,
        "p_layers": p,
        "gammas": list(gammas),
        "betas": list(betas),
        "uses_adjacency": adjacency is not None,
    }
    return qc


# -----------------------------------------------------------------------------
# CLI convenience
# -----------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import argparse
    from qiskit.visualization import circuit_drawer
    import ast

    parser = argparse.ArgumentParser(description="Generate generic QAOA circuit and save image.")
    parser.add_argument("n", type=int, help="Number of qubits")
    parser.add_argument("p", type=int, help="Number of QAOA layers")
    parser.add_argument("--adj", help="Adjacency matrix as Python literal (e.g. '[[0,1],[1,0]]')")
    parser.add_argument("--outfile", default="qaoa_generic.svg", help="Output filename")
    args = parser.parse_args()

    adj_mat = ast.literal_eval(args.adj) if args.adj else None

    qc_cli = generate(n=args.n, p=args.p, adjacency=adj_mat, measure=True)
    circuit_drawer(qc_cli, output="mpl", filename=args.outfile, style="iqp")
    print(f"Saved to {args.outfile}")
