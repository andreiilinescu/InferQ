"""inferq_dataset.manifest_utils
=================================
Reusable helpers for loading and querying the MANIFEST.parquet file
and for fetching individual circuits by their *circuit_id*.

All paths are **relative to the project root** that contains the
`circuits/` directory and `MANIFEST.parquet`.  Override them if you
mount the dataset elsewhere (e.g. in a notebook or a cluster job).

Example
-------
```python
from inferq_dataset.manifest_utils import (
    load_manifest, filter_circuits, load_circuit
)

# Load the whole manifest
mf = load_manifest()
print(mf.head())

# Find all circuits with ≤50 qubits that the model says are 'mps'
subset = filter_circuits(mf, max_qubits=50, rec_sim="mps")
print(len(subset), "circuits match")

# Materialise one circuit
qc = load_circuit(subset.iloc[0].circuit_id)
qc.draw("text")
```
"""

from __future__ import annotations

import json
import pathlib
import typing as _t

import pandas as _pd

try:
    import qiskit.qpy as _qpy
except ImportError:  # pragma: no cover – optional at import time
    _qpy = None  # type: ignore

__all__ = [
    "PROJECT_ROOT",
    "MANIFEST_PATH",
    "CIRCUITS_ROOT",
    "load_manifest",
    "get_meta_row",
    "filter_circuits",
    "circuit_dir",
    "load_circuit",
    "iter_circuits",
]

# ---------------------------------------------------------------------------
# Config – change these if your dataset sits elsewhere
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]  # inferq_dataset/
MANIFEST_PATH = PROJECT_ROOT / "MANIFEST.parquet"
CIRCUITS_ROOT = PROJECT_ROOT / "circuits"


# ---------------------------------------------------------------------------
# Core loaders
# ---------------------------------------------------------------------------


def load_manifest(
    path: pathlib.Path | str | None = None, *, columns: list[str] | None = None
) -> _pd.DataFrame:
    """Load *MANIFEST.parquet* into a :class:`pandas.DataFrame`.

    Parameters
    ----------
    path
        Custom location of the Parquet file.  Defaults to
        :data:`MANIFEST_PATH`.
    columns
        Optional list of columns to load (pass-through to
        :pyfunc:`pandas.read_parquet(columns=...)`).  Useful when you only need
        a handful of metadata fields and want to save RAM.
    """
    if path is None:
        path = MANIFEST_PATH
    return _pd.read_parquet(path, columns=columns)


def get_meta_row(
    circuit_id: str | int, manifest: _pd.DataFrame | None = None
) -> _pd.Series:
    """Return the *meta.json* row for a single circuit by *circuit_id*.

    ``manifest`` may be omitted; in that case the function will call
    :func:`load_manifest` implicitly.
    """
    if manifest is None:
        manifest = load_manifest()
    row = manifest.loc[manifest["circuit_id"] == str(circuit_id)]
    if row.empty:
        raise KeyError(f"circuit_id '{circuit_id}' not found in manifest")
    return row.iloc[0]


# ---------------------------------------------------------------------------
# Circuit helpers
# ---------------------------------------------------------------------------


def circuit_dir(
    circuit_id: str | int, *, circuits_root: pathlib.Path | None = None
) -> pathlib.Path:
    """Return the directory that contains *circuit.qpy* & *meta.json* for *circuit_id*."""
    if circuits_root is None:
        circuits_root = CIRCUITS_ROOT
    return circuits_root / str(circuit_id)


def load_circuit(
    circuit_id: str | int, *, circuits_root: pathlib.Path | None = None
):  # -> QuantumCircuit
    """Load the :class:`qiskit.QuantumCircuit` stored in *circuit.qpy*.

    Requires Qiskit Terra ≥1.4.  Raises :class:`ImportError` if *qiskit* is not
    available.
    """
    if _qpy is None:
        raise ImportError(
            "qiskit is not installed; install qiskit-terra>=1.4 to load circuits"
        )
    qpy_file = circuit_dir(circuit_id, circuits_root=circuits_root) / "circuit.qpy"
    with open(qpy_file, "rb") as f:
        return _qpy.load(f)[0]


# ---------------------------------------------------------------------------
# Filtering utilities
# ---------------------------------------------------------------------------


def filter_circuits(
    df: _pd.DataFrame,
    /,
    *,
    min_qubits: int | None = None,
    max_qubits: int | None = None,
    rec_sim: str | None = None,
    cond: str | None = None,
) -> _pd.DataFrame:
    """Return a *view* (not a copy) of *df* with the given filters applied.

    Parameters
    ----------
    min_qubits, max_qubits
        Inclusive bounds on the ``n_qubits`` column.
    rec_sim
        Restrict to circuits whose *recommended simulator* label matches this
        string (e.g. ``"mps"``).
    cond
        Extra pandas query string, e.g. ``"t_count > 10 and bond_dim_est < 32"``.
    """
    subset = df
    if min_qubits is not None:
        subset = subset[subset["n_qubits"] >= min_qubits]
    if max_qubits is not None:
        subset = subset[subset["n_qubits"] <= max_qubits]
    if rec_sim is not None:
        subset = subset[subset["rec_sim"] == rec_sim]
    if cond:
        subset = subset.query(cond, engine="python")
    return subset


# ---------------------------------------------------------------------------
# High‑level iterator
# ---------------------------------------------------------------------------


def iter_circuits(
    df: _pd.DataFrame | None = None,
    *,
    circuits_root: pathlib.Path | None = None,
    load: bool = False,
    columns: list[str] | None = None,
):
    """Yield *(meta, circuit)* pairs (or *(meta, None)* if ``load=False``).

    Parameters
    ----------
    df
        Subset of the manifest.  If *None*, the full manifest is loaded.
    load
        If *True*, also load the :class:`qiskit.QuantumCircuit` from disk.
    columns
        Columns of the manifest to keep when iterating (helps save RAM when you
        only need a few fields).

    Yields
    ------
    tuple(meta: pandas.Series, circuit: QuantumCircuit | None)
    """
    if df is None:
        df = load_manifest(columns=columns)
    for _, row in df.iterrows():
        circ = (
            load_circuit(row.circuit_id, circuits_root=circuits_root) if load else None
        )
        yield row, circ


if __name__ == "__main__":
    # Test the module
    mf = load_manifest()
    print(mf.head())
    # subset = filter_circuits(mf, max_qubits=50, rec_sim="mps")
    # print(len(mf), "circuits match")
    for meta, circ in iter_circuits(mf, load=True):
        print(meta.circuit_id, circ)
        break  # just one
