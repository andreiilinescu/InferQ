#!/usr/bin/env python3
"""
Simple test script to verify the CircuitMerger hierarchical generation system.
"""

from generators.circuit_merger import CircuitMerger
from generators.lib.generator import BaseParams


def simple_test():
    """
    Simple test to verify the basic functionality works.
    """
    print("Testing CircuitMerger with NumPy-optimized probability system...")

    # Create simple base parameters
    base_params = BaseParams(
        max_qubits=4, min_qubits=4, max_depth=10, min_depth=10, seed=42
    )

    # Initialize the circuit merger
    merger = CircuitMerger(base_params)
    print(f"Initialized CircuitMerger with {len(merger.generators)} generators")

    # Generate a simple hierarchical circuit
    print("\nGenerating hierarchical circuit...")
    circuit = merger.generate_hierarchical_circuit(
        stopping_probability=0.5, max_generators=2
    )

    if circuit and circuit.data:
        print(f"\n✓ SUCCESS: Generated circuit '{circuit.name}'")
        print(f"  - Qubits: {circuit.num_qubits}")
        print(f"  - Depth: {circuit.depth()}")
        print(f"  - Total operations: {len(circuit.data)}")

        # Count gate types
        gate_counts = {}
        for instruction in circuit.data:
            gate_name = instruction.operation.name
            gate_counts[gate_name] = gate_counts.get(gate_name, 0) + 1

        print(f"  - Gate types: {list(gate_counts.keys())}")
        return True
    else:
        print("✗ FAILED: No circuit generated or empty circuit")
        return False


if __name__ == "__main__":
    try:
        success = simple_test()
        if success:
            print("\n🎉 Test completed successfully!")
        else:
            print("\n❌ Test failed!")
    except Exception as e:
        print(f"\n💥 Error during test: {e}")
        import traceback

        traceback.print_exc()
