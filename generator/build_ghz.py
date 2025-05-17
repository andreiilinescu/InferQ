#!/usr/bin/env python
import sys, pathlib, qiskit
from utils.feature_extractors import extract_all
from utils.save_utils import save_circuit


def ghz(n):
    qc = qiskit.QuantumCircuit(n)
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    return qc


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    circ = ghz(n)
    feats = extract_all(circ)
    save_circuit(circ, feats, pathlib.Path("circuits"))
