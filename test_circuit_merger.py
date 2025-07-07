#!/usr/bin/env python3
"""
Test script for the CircuitMerger hierarchical quantum circuit generation system.

This script demonstrates how to use the probability-based generator selection
to create hierarchical quantum circuits with adaptive probabilities.
"""

import numpy as np
from generators.circuit_merger import CircuitMerger
from generators.lib.generator import BaseParams


def test_basic_hierarchical_generation():
    """
    Test basic hierarchical circuit generation with equal probabilities.
    """
    print("=" * 60)
    print("TEST 1: Basic Hierarchical Generation")
    print("=" * 60)

    # Create base parameters for circuit generation
    base_params = BaseParams(
        max_qubits=8, min_qubits=8, max_depth=20, min_depth=20, seed=42
    )

    # Initialize the circuit merger
    merger = CircuitMerger(base_params)

    # Generate a hierarchical circuit with default settings
    circuit = merger.generate_hierarchical_circuit(
        stopping_probability=0.4, max_generators=3
    )

    print(f"\nGenerated circuit: {circuit.name}")
    print(f"Total qubits: {circuit.num_qubits}")
    print(f"Total depth: {circuit.depth()}")
    print(f"Total gates: {len(circuit.data)}")

    return circuit


def test_biased_state_prep_generation():
    """
    Test hierarchical generation with bias toward state preparation circuits.
    """
    print("\n" + "=" * 60)
    print("TEST 2: Biased State Preparation Generation")
    print("=" * 60)

    # Create base parameters
    base_params = BaseParams(
        max_qubits=6, min_qubits=6, max_depth=15, min_depth=15, seed=123
    )

    merger = CircuitMerger(base_params)

    # Create probability distribution favoring state preparation circuits
    num_generators = len(merger.generators)
    probabilities = np.ones(num_generators)

    # Boost state preparation circuits
    state_prep_names = {
        "GHZ",
        "WState",
        "GraphState",
        "RandomCircuit",
        "EfficientU2",
        "RealAmplitudes",
        "TwoLocal",
    }

    for i, gen in enumerate(merger.generators):
        if gen.__class__.__name__ in state_prep_names:
            probabilities[i] = 3.0  # 3x higher probability
        else:
            probabilities[i] = 1.0

    print("Using biased probabilities favoring state preparation circuits...")

    circuit = merger.generate_hierarchical_circuit(
        generators_probabilities=probabilities,
        stopping_probability=0.3,
        max_generators=4,
    )

    print(f"\nGenerated circuit: {circuit.name}")
    print(f"Total qubits: {circuit.num_qubits}")
    print(f"Total depth: {circuit.depth()}")

    return circuit


def test_algorithm_focused_generation():
    """
    Test hierarchical generation with bias toward algorithm circuits.
    """
    print("\n" + "=" * 60)
    print("TEST 3: Algorithm-Focused Generation")
    print("=" * 60)

    base_params = BaseParams(
        max_qubits=10, min_qubits=10, max_depth=25, min_depth=25, seed=456
    )

    merger = CircuitMerger(base_params)

    # Create probability distribution favoring algorithm circuits
    num_generators = len(merger.generators)
    probabilities = np.ones(num_generators)

    # Boost algorithm circuits
    algorithm_names = {
        "AmplitudeEstimation",
        "DeutschJozsa",
        "GroverNoAncilla",
        "GroverVChain",
        "QAOA",
        "QFTGenerator",
        "QNN",
        "QuantumWalk",
        "QPE",
        "VQEGenerator",
    }

    for i, gen in enumerate(merger.generators):
        if gen.__class__.__name__ in algorithm_names:
            probabilities[i] = 2.5  # 2.5x higher probability
        else:
            probabilities[i] = 1.0

    print("Using biased probabilities favoring algorithm circuits...")

    circuit = merger.generate_hierarchical_circuit(
        generators_probabilities=probabilities,
        stopping_probability=0.2,  # Lower stopping probability for more circuits
        max_generators=5,
    )

    print(f"\nGenerated circuit: {circuit.name}")
    print(f"Total qubits: {circuit.num_qubits}")
    print(f"Total depth: {circuit.depth()}")

    return circuit


def test_synergy_demonstration():
    """
    Demonstrate the synergy system by forcing specific generator combinations.
    """
    print("\n" + "=" * 60)
    print("TEST 4: Synergy Demonstration (QFT + QPE)")
    print("=" * 60)

    base_params = BaseParams(
        max_qubits=8, min_qubits=8, max_depth=30, min_depth=30, seed=789
    )

    merger = CircuitMerger(base_params)

    # Create probability distribution that strongly favors QFT
    num_generators = len(merger.generators)
    probabilities = np.ones(num_generators) * 0.1  # Low base probability

    for i, gen in enumerate(merger.generators):
        if gen.__class__.__name__ == "QFTGenerator":
            probabilities[i] = 10.0  # Very high probability for QFT
        elif gen.__class__.__name__ == "QPE":
            probabilities[i] = 1.0  # Normal probability for QPE

    print("Starting with high QFT probability to demonstrate QFT→QPE synergy...")

    circuit = merger.generate_hierarchical_circuit(
        generators_probabilities=probabilities,
        stopping_probability=0.1,  # Very low stopping probability
        max_generators=3,
    )

    print(f"\nGenerated circuit: {circuit.name}")
    print(f"Total qubits: {circuit.num_qubits}")
    print(f"Total depth: {circuit.depth()}")

    return circuit


def test_multiple_generations():
    """
    Test generating multiple circuits to show variety in outputs.
    """
    print("\n" + "=" * 60)
    print("TEST 5: Multiple Generation Variety")
    print("=" * 60)

    base_params = BaseParams(
        max_qubits=6,
        min_qubits=6,
        max_depth=20,
        min_depth=20,
        seed=None,  # Different seed each time
    )

    merger = CircuitMerger(base_params)

    circuits = []
    for i in range(3):
        print(f"\n--- Generation {i+1} ---")
        circuit = merger.generate_hierarchical_circuit(
            stopping_probability=0.35, max_generators=4
        )
        circuits.append(circuit)
        print(
            f"Circuit {i+1}: {circuit.name} - {circuit.num_qubits}q, depth={circuit.depth()}"
        )

    return circuits


def analyze_circuit_composition(circuit):
    """
    Analyze the composition of a generated circuit.
    """
    if not circuit.data:
        print("Empty circuit - no analysis possible")
        return

    print(f"\n--- Circuit Analysis for {circuit.name} ---")
    print(f"Number of qubits: {circuit.num_qubits}")
    print(f"Number of classical bits: {circuit.num_clbits}")
    print(f"Circuit depth: {circuit.depth()}")
    print(f"Total operations: {len(circuit.data)}")

    # Count different types of operations
    gate_counts = {}
    for instruction in circuit.data:
        gate_name = instruction.operation.name
        gate_counts[gate_name] = gate_counts.get(gate_name, 0) + 1

    print("Gate composition:")
    for gate, count in sorted(gate_counts.items()):
        print(f"  {gate}: {count}")


def main():
    """
    Run all test cases and demonstrate the hierarchical circuit generation system.
    """
    print("Hierarchical Quantum Circuit Generation Test Suite")
    print("Using NumPy-optimized probability adaptation system")

    try:
        # Test 1: Basic generation
        circuit1 = test_basic_hierarchical_generation()
        analyze_circuit_composition(circuit1)

        # Test 2: State prep bias
        circuit2 = test_biased_state_prep_generation()
        analyze_circuit_composition(circuit2)

        # Test 3: Algorithm focus
        circuit3 = test_algorithm_focused_generation()
        analyze_circuit_composition(circuit3)

        # Test 4: Synergy demonstration
        circuit4 = test_synergy_demonstration()
        analyze_circuit_composition(circuit4)

        # Test 5: Multiple generations
        circuits = test_multiple_generations()
        for i, circuit in enumerate(circuits):
            print(f"\n--- Analysis for Generation {i+1} ---")
            analyze_circuit_composition(circuit)

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)

        # Save one example circuit for inspection
        if circuit1 and circuit1.data:
            print("\nSaving example circuit to 'example_hierarchical_circuit.qasm'")
            try:
                with open("example_hierarchical_circuit.qasm", "w") as f:
                    f.write(circuit1.qasm())
                print("Circuit saved successfully!")
            except Exception as e:
                print(f"Could not save circuit: {e}")

    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
