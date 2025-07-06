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


def depth(min_depth: int, max_depth: int, seed: int = None) -> int:
    """
    Generate a random depth for a quantum circuit.

    :param min_depth: Minimum depth of the circuit.
    :param max_depth: Maximum depth of the circuit.
    :param seed: Random seed for reproducibility.
    :return: Random depth value.
    """
    if seed is not None:
        random.seed(seed)
    return random.randint(min_depth, max_depth)


def adjacency_graph(
    num_qubits: int, seed: int = None, p: float = 0.5, return_edges: bool = False
) -> list[list[int]]:
    """
    Generate a random graph using NetworkX's G(n, p) model,
    returning either an adjacency matrix or adjacency list.

    :param num_qubits: Number of nodes (qubits).
    :param seed: Random seed for reproducibility.
    :param p: Edge‐presence probability (default 0.5).
    :param adjacency_list: If True, return adjacency list; else adjacency matrix.
    :return: Either a nested list-of-lists adjacency matrix (0/1)
             or adjacency list ([[neighbors_of_0], [neighbors_of_1], …]).
    """
    G = nx.gnp_random_graph(num_qubits, p, seed=seed, directed=False)

    if return_edges:
        # Return each undirected edge once as [u, v]
        return [[u, v] for u, v in G.edges()]
    else:
        # Convert to dense adjacency matrix
        A = nx.to_numpy_array(G, dtype=int)
        return A.astype(int).tolist()


def reps(min_reps: int, max_reps: int, seed: int = None) -> int:
    """
    Generate a random number of repetitions for a quantum circuit.

    :param min_reps: Minimum number of repetitions.
    :param max_reps: Maximum number of repetitions.
    :param seed: Random seed for reproducibility.
    :return: Random number of repetitions.
    """
    if seed is not None:
        random.seed(seed)
    return random.randint(min_reps, max_reps)


def entanglement_pattern(num_qubits: int, seed: int = None) -> str:
    """
    Generate a random entanglement pattern for a quantum circuit.

    :param num_qubits: Number of qubits in the circuit.
    :param seed: Random seed for reproducibility.
    :return: Entanglement pattern as a string.
    """
    random.seed(seed) if seed is not None else None
    if random.choice([False, True]):
        return entanglement_pattern_string(seed)
    else:
        g = adjacency_graph(
            num_qubits,
            seed,
            p=random.uniform(0.1, 0.9),  # Random probability for edge creation
            return_edges=True,
        )
        print("Generated adjacency graph:", g)
        return g


def entanglement_pattern_string(seed: int = None) -> str:
    """
    Generate a random entanglement pattern for a quantum circuit.

    :param seed: Random seed for reproducibility.
    :return: Entanglement pattern as a string.
    """
    patterns = ["linear", "full", "circular", "reverse_linear"]
    if seed is not None:
        random.seed(seed)
    return random.choice(patterns)


def random_parameter_values(
    num_params: int, seed: int = None, min_val: float = 0.0, max_val: float = 2 * 3.14159
) -> list[float]:
    """
    Generate a list of random parameter values for quantum circuits.

    :param num_params: Number of parameters needed.
    :param seed: Random seed for reproducibility.
    :param min_val: Minimum value for parameters (default: 0.0).
    :param max_val: Maximum value for parameters (default: 2π).
    :return: List of random parameter values.
    """
    if seed is not None:
        random.seed(seed)
    return [random.uniform(min_val, max_val) for _ in range(num_params)]
