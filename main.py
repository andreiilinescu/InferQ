import sys
from generators.circuit_merger import CircuitMerger
from generators.lib.generator import BaseParams


def main():
    """
    Main function to demonstrate hierarchical quantum circuit generation.
    """
    print("🚀 Starting InferQ Hierarchical Circuit Generation!")

    # Get number of qubits from command line argument
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"Generating circuits with {n} qubits")

    # Create base parameters
    base_params = BaseParams(
        max_qubits=n, min_qubits=n, max_depth=10, min_depth=5, seed=42
    )

    # Initialize circuit merger
    circ_merger = CircuitMerger(base_params=base_params)
    print(f"Initialized with {len(circ_merger.generators)} available generators")

    # Generate hierarchical circuit
    print("\n" + "=" * 50)
    circ = circ_merger.generate_hierarchical_circuit(
        stopping_probability=0.4, max_generators=3
    )
    print("=" * 50)

    # Display results
    if circ and circ.data:
        print(f"\n✅ Successfully generated circuit: {circ.name}")
        print(
            f"   📊 Stats: {circ.num_qubits} qubits, depth={circ.depth()}, {len(circ.data)} operations"
        )

        # Count gate types
        gate_counts = {}
        for instruction in circ.data:
            gate_name = instruction.operation.name
            gate_counts[gate_name] = gate_counts.get(gate_name, 0) + 1

        print(
            f"   🔧 Gates: {dict(list(gate_counts.items())[:5])}{'...' if len(gate_counts) > 5 else ''}"
        )

        print("\n🔬 Circuit Visualization:")
        print(circ)

        # Save circuit to file
        try:
            filename = f"hierarchical_circuit_{n}q.qasm"
            with open(filename, "w") as f:
                f.write(circ)
            print(f"💾 Circuit saved to: {filename}")
        except Exception as e:
            print(f"⚠️  Could not save circuit: {e}")

    else:
        print("❌ No circuit was generated or circuit is empty")
        return 1

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n💥 Error during execution: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
