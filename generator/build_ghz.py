#!/usr/bin/env python
import sys, pathlib, qiskit

def ghz(n):
    qc = qiskit.QuantumCircuit(n)
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    return qc


