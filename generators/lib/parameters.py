import random
import networkx as nx


def num_qbits(min_qubits: int, max_qubits: int, seed: int = None) -> int:
    """
    Generate a random number of qubits between the specified limits.

    :param max_qubits: Maximum number of qubits.
    :param min_qubits: Minimum number of qubits.
    :return: Random number of qubits.
    """
    if seed is not None:
        random.seed(seed)
    return random.randint(min_qubits, max_qubits)


def adjacency_graph(
    num_qubits: int, seed: int = None, p: float = 0.5
) -> list[list[int]]:
    """
    Generate a random adjacency matrix using NetworkX's G(n, p) model.

    :param num_qubits: Number of nodes (qubits).
    :param seed: Random seed for reproducibility.
    :param p: Probability of each edge being present (default 0.5).
    :return: Adjacency matrix as a list of lists of 0/1.
    """
    # G(n, p) with given seed
    G = nx.gnp_random_graph(num_qubits, p, seed=seed, directed=False)

    # Convert to NumPy array (dtype=int) then to nested lists
    # Note: for very large graphs you might prefer sparse matrices
    A = nx.to_numpy_array(G, dtype=int)
    return A.astype(int).tolist()
