from qiskit.circuit import QuantumCircuit, QuantumRegister

# Using medium article and MQT implementation
# Defining coin and then 

# BASED ON MQT BENCH's implementation
def generate(n: int,depth: int, coin_state_preparation: QuantumCircuit = None):
    n = n -1

    coin = QuantumRegister(1, "coin")
    node = QuantumRegister(n, "graphnode")

    qc = QuantumCircuit(node, coin, name="qwalk")
    
    # coin state preparation
    if coin_state_preparation is not None:
        qc.append(coin_state_preparation, coin[:])

    for _ in range(depth):
        # Hadamard coin operator
        qc.h(coin)

        # controlled increment
        for i in range(n - 1):
            qc.mcx(coin[:] + node[i + 1 :], node[i])
        qc.cx(coin, node[n - 1])

        # controlled decrement
        qc.x(coin)
        qc.x(node[1:])
        for i in range(n - 1):
            qc.mcx(coin[:] + node[i + 1 :], node[i])
        qc.cx(coin, node[n - 1])
        qc.x(node[1:])
        qc.x(coin)
    
    return qc