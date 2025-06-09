from qiskit.circuit.library import efficient_su2

def efficientU2(n, eng, reps):
    qc = efficient_su2(n, entanglement=eng, reps=reps)
    qc.name='efficientU2'
    return qc