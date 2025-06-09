from qiskit import QuantumCircuit, QuantumRegister
import numpy as np

def wstate(n):
    qc = QuantumCircuit(n, name=f"Wstate({n})")
    # Could use G gate approach, but using f gate approach like MQT bench? 

    q = QuantumRegister(n, "q")
    qcirc = QuantumCircuit(q, name="wstate")

    # MQT bench f_gate. 
    def f_gate(qc: QuantumCircuit, q: QuantumRegister, i: int, j: int, n: int, k: int) -> None:
        theta = np.arccos(np.sqrt(1/(n - k + 1)))
        qc.ry(-theta, q[j])
        qc.cz(q[i], q[j])
        qc.ry(theta, q[j])

    qcirc.x(q[-1])
    
    for m in range(1, n):
        f_gate(qc, q, n - m, n - m - 1, n, m)

    for k in reversed(range(1, n)):
        qcirc.cx(k - 1, k)

    return qcirc
