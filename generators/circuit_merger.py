from typing import List, Union
from qiskit import QuantumCircuit
import random
import numpy as np

from generators.lib.generator import Generator, BaseParams

# Import all state preparation circuits
from generators.state_prep_circuits.ghz import GHZ
from generators.state_prep_circuits.wstate import WState
from generators.state_prep_circuits.graph_state import GraphState
from generators.state_prep_circuits.random_circuit import RandomCircuit
from generators.state_prep_circuits.effu2 import EfficientU2
from generators.state_prep_circuits.realamp_ansatz_rand import RealAmplitudes
from generators.state_prep_circuits.two_local_rand import TwoLocal

# Import all algorithm circuits
from generators.algorithms.amplitude_estimation.amplitude_estimation_class import (
    AmplitudeEstimation,
)
from generators.algorithms.deutsch_jozsa.deutsch_jozsa_class import DeutschJozsa
from generators.algorithms.grover_no_ancilla.grover_no_ancilla_class import (
    GroverNoAncilla,
)
from generators.algorithms.grover_v_chain.grover_v_chain_class import GroverVChain
from generators.algorithms.qaoa import QAOA
from generators.algorithms.qft import QFTGenerator
from generators.algorithms.qnn import QNN
from generators.algorithms.qwalk import QuantumWalk
from generators.algorithms.qpe import QPE
from generators.algorithms.vqe import VQEGenerator

# Complete list of all generator classes
ALL_GENERATOR_CLASSES = [
    # State preparation circuits
    GHZ,
    WState,
    GraphState,
    RandomCircuit,
    EfficientU2,
    RealAmplitudes,
    TwoLocal,
    # Algorithm circuits
    AmplitudeEstimation,
    DeutschJozsa,
    GroverNoAncilla,
    GroverVChain,
    QAOA,
    QFTGenerator,
    QNN,
    QuantumWalk,
    QPE,
    VQEGenerator,
]

# Dictionary mapping class names to classes for easy access
GENERATOR_CLASS_MAP = {cls.__name__: cls for cls in ALL_GENERATOR_CLASSES}


class CircuitMerger:
    """
    Class to merge multiple quantum circuits into a single hierarchical circuit.
    """

    def __init__(self, base_params: BaseParams):
        self.base_params = base_params
        self.generators = self.initialize_generators()

    def initialize_generators(self) -> List[Generator]:
        """
        Initialize all generator classes with the base parameters.

        Returns:
            List[Generator]: List of initialized generator instances.
        """
        return [cls(self.base_params) for cls in ALL_GENERATOR_CLASSES]

    def select_generators_by_probability(
        self,
        generators_probabilities: Union[List[float], np.ndarray],
        stopping_probability: float,
        max_generators: int,
    ) -> List[Generator]:
        """
        Select generators based on probability distribution for hierarchical generation.
        This is the foundation for your probability-based generation system.

        Args:
            generators_probabilities: List of probabilities for each generator
            stopping_probability: Probability to stop adding more generators
            max_generators: Maximum number of generators to select

        Returns:
            List of selected generators
        """

        selected = []

        # Create mapping from generator class to index for probability updates
        generator_to_index = {
            gen.__class__.__name__: i for i, gen in enumerate(self.generators)
        }

        # Normalize probabilities using NumPy
        generators_probabilities = np.array(generators_probabilities)
        total_prob = np.sum(generators_probabilities)
        if total_prob > 0:
            current_probs = generators_probabilities / total_prob
        else:
            current_probs = np.ones(len(self.generators)) / len(self.generators)

        for step in range(max_generators):
            # Print current probability distribution for transparency
            if step == 0:
                print("\nInitial probability distribution:")
                self._print_probability_distribution(current_probs, step)

            # Check if we should stop (except for first generator)
            if step > 0 and random.random() < stopping_probability:
                print(
                    f"Stopping generation at step {step} (stopping_prob={stopping_probability:.3f})"
                )
                break

            # Select generator based on current probability distribution
            if self.generators:
                # Use weighted random selection from all generators
                selected_generator = random.choices(
                    self.generators, weights=current_probs, k=1
                )[0]
                selected.append(selected_generator)

                print(
                    f"Step {step + 1}: Selected {selected_generator.__class__.__name__}"
                )

                # Update probabilities based on conditional dependencies P(gens | prev_gen)
                self._update_conditional_probabilities(
                    current_probs, selected_generator, generator_to_index
                )

                # Print updated probabilities
                if step < max_generators - 1:  # Don't print on last iteration
                    self._print_probability_distribution(current_probs, step + 1)

                # Adapt stopping probability to avoid infinite repetition
                # Increase stopping probability with each step to encourage termination
                stopping_probability = min(0.9, stopping_probability)
                print(f"Updated stopping probability: {stopping_probability:.3f}")
            else:
                # No generators available (shouldn't happen)
                print("No generators available")
                break

        return selected

    def generate_hierarchical_circuit(
        self,
        generators_probabilities: Union[List[float], np.ndarray] = None,
        stopping_probability: float = 0.3,
        max_generators: int = 5,
    ) -> QuantumCircuit:
        """
        Generate circuit using probability-based hierarchical selection.
        This is your transition method to probability-based generation!

        Args:
            generators_probabilities: Probability weights for each generator (optional)
            stopping_probability: Probability to stop after each generator
            max_generators: Maximum generators in the hierarchy

        Returns:
            Hierarchically generated quantum circuit
        """
        if generators_probabilities is None:
            # Equal probability for all generators initially
            generators_probabilities = np.ones(len(self.generators))

        print(
            f"Starting hierarchical generation with {len(self.generators)} available generators..."
        )
        print(
            f"Stopping probability: {stopping_probability}, Max generators: {max_generators}"
        )

        # Select generators based on probability
        selected_generators = self.select_generators_by_probability(
            generators_probabilities, stopping_probability, max_generators
        )

        if not selected_generators:
            print("No generators selected!")
            return QuantumCircuit()

        print(
            f"Selected {len(selected_generators)} generators for hierarchical circuit"
        )

        # Generate circuits from selected generators only
        successful_circuits = []
        for generator in selected_generators:
            try:
                print(f"Generating parameters for {generator.__class__.__name__}...")
                params = generator.generate_parameters()

                print(f"Generating circuit for {generator.__class__.__name__}...")
                if isinstance(params, tuple):
                    circuit = generator.generate(*params)
                elif isinstance(params, dict):
                    circuit = generator.generate(**params)
                else:
                    circuit = generator.generate(params)

                if circuit is not None and hasattr(circuit, "data"):
                    circuit.name = generator.__class__.__name__
                    successful_circuits.append(circuit)
                    print(
                        f"✓ Generated {circuit.name}: {circuit.num_qubits}q, depth={circuit.depth()}"
                    )
                else:
                    print(
                        f"✗ {generator.__class__.__name__} returned None or invalid circuit"
                    )

            except Exception as e:
                print(
                    f"✗ Error with {generator.__class__.__name__}: {type(e).__name__}: {e}"
                )
                # Print more detailed error for debugging
                import traceback

                print(f"   Details: {traceback.format_exc().splitlines()[-2]}")
                continue

        # Merge the successful circuits
        if not successful_circuits:
            return QuantumCircuit()

        max_qubits = max(c.num_qubits for c in successful_circuits)
        max_clbits = max(c.num_clbits for c in successful_circuits)

        merged_circuit = QuantumCircuit(max_qubits, max_clbits)
        merged_circuit.name = f"HierarchicalCircuit_{len(successful_circuits)}gens"

        for i, circuit in enumerate(successful_circuits):
            try:
                if i > 0:
                    merged_circuit.barrier()

                target_qubits = list(range(min(circuit.num_qubits, max_qubits)))
                target_clbits = (
                    list(range(min(circuit.num_clbits, max_clbits)))
                    if circuit.num_clbits > 0
                    else None
                )

                if target_clbits is not None:
                    merged_circuit.compose(
                        circuit,
                        qubits=target_qubits,
                        clbits=target_clbits,
                        inplace=True,
                    )
                else:
                    merged_circuit.compose(circuit, qubits=target_qubits, inplace=True)

            except Exception as e:
                print(f"✗ Failed to compose {circuit.name}: {e}")
                continue

        return merged_circuit

    def _update_conditional_probabilities(
        self,
        current_probs: np.ndarray,
        selected_generator: Generator,
        generator_to_index: dict,
    ) -> None:
        """
        Update probability distribution based on the previously selected generator.
        Implements P(gens | prev_gen) conditional probability adaptation.

        Args:
            current_probs: Current probability distribution to modify (NumPy array)
            selected_generator: The generator that was just selected
            generator_to_index: Mapping from generator names to indices
        """
        selected_name = selected_generator.__class__.__name__

        # Define compatibility/synergy rules between different generator types
        # These heuristics encourage meaningful hierarchical combinations

        # Categorize generators by type and characteristics
        state_prep_generators = {
            "GHZ",
            "WState",
            "GraphState",
            "RandomCircuit",
            "EfficientU2",
            "RealAmplitudes",
            "TwoLocal",
        }
        algorithm_generators = {
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
        variational_generators = {
            "VQEGenerator",
            "QAOA",
            "QNN",
            "RealAmplitudes",
            "TwoLocal",
        }
        entangling_generators = {
            "GHZ",
            "WState",
            "GraphState",
            "EfficientU2",
            "QuantumWalk",
        }

        print(f"Updating probabilities based on selected: {selected_name}")

        # Store original probabilities for logging
        original_probs = current_probs.copy()

        # Create boolean masks for efficient operations
        gen_names = [gen.__class__.__name__ for gen in self.generators]
        gen_names_array = np.array(gen_names)

        # Mask for the selected generator (reduce repetition probability)
        selected_mask = gen_names_array == selected_name
        current_probs[selected_mask] *= 0.3

        # Create category masks
        state_prep_mask = np.array(
            [name in state_prep_generators for name in gen_names]
        )
        algorithm_mask = np.array([name in algorithm_generators for name in gen_names])
        variational_mask = np.array(
            [name in variational_generators for name in gen_names]
        )
        entangling_mask = np.array(
            [name in entangling_generators for name in gen_names]
        )

        if selected_name in state_prep_generators:
            # Boost algorithm generators after state prep
            current_probs[algorithm_mask] *= 1.5
            # Reduce other state prep circuits (excluding the selected one)
            other_state_prep_mask = state_prep_mask & ~selected_mask
            current_probs[other_state_prep_mask] *= 0.6

        elif selected_name in algorithm_generators:
            # Reduce other algorithms (excluding the selected one)
            other_algorithm_mask = algorithm_mask & ~selected_mask
            current_probs[other_algorithm_mask] *= 0.7
            # Boost state prep for variety
            current_probs[state_prep_mask] *= 1.3

        # Apply specific synergies using vectorized operations
        self._apply_specific_synergies(
            current_probs,
            selected_name,
            gen_names_array,
            variational_mask,
            entangling_mask,
        )

        # Log significant probability changes
        significant_changes = np.abs(current_probs - original_probs) > 0.01
        for i in np.where(significant_changes)[0]:
            gen_name = gen_names[i]
            original_prob = original_probs[i]
            new_prob = current_probs[i]
            change_factor = new_prob / original_prob if original_prob > 0 else 0
            print(
                f"  {gen_name}: {original_prob:.3f} -> {new_prob:.3f} (×{change_factor:.2f})"
            )

        # Renormalize probabilities
        current_probs /= np.sum(current_probs)

    def _apply_specific_synergies(
        self,
        current_probs: np.ndarray,
        selected_name: str,
        gen_names_array: np.ndarray,
        variational_mask: np.ndarray,
        entangling_mask: np.ndarray,
    ) -> None:
        """
        Apply specific synergy rules using vectorized NumPy operations.
        """
        # QFT and QPE synergies
        if selected_name == "QFTGenerator":
            qpe_mask = gen_names_array == "QPE"
            current_probs[qpe_mask] *= 2.5
        elif selected_name == "QPE":
            qft_mask = gen_names_array == "QFTGenerator"
            current_probs[qft_mask] *= 2.0

        # GHZ synergies
        elif selected_name == "GHZ":
            ghz_synergy_mask = np.isin(
                gen_names_array, ["QuantumWalk", "QAOA", "VQEGenerator"]
            )
            current_probs[ghz_synergy_mask] *= 1.4

        # Variational generator synergies
        elif selected_name in {"VQEGenerator", "QAOA", "QNN"}:
            ansatz_mask = np.isin(gen_names_array, ["RealAmplitudes", "TwoLocal"])
            current_probs[ansatz_mask] *= 1.6

        # Entangling generator synergies
        elif selected_name in {
            "GHZ",
            "WState",
            "GraphState",
            "EfficientU2",
            "QuantumWalk",
        }:
            oracle_mask = np.isin(gen_names_array, ["DeutschJozsa", "GroverNoAncilla"])
            current_probs[oracle_mask] *= 1.3

        # Graph state and quantum walk specific synergy
        if selected_name == "GraphState":
            qwalk_mask = gen_names_array == "QuantumWalk"
            current_probs[qwalk_mask] *= 1.7

    def _print_probability_distribution(
        self, current_probs: np.ndarray, step: int
    ) -> None:
        """
        Print current probability distribution for debugging and transparency.

        Args:
            current_probs: Current probability distribution (NumPy array)
            step: Current step in the generation process
        """
        print(f"\n--- Probability Distribution at Step {step} ---")
        # Use NumPy boolean indexing for efficient filtering
        significant_mask = current_probs > 0.01
        significant_indices = np.where(significant_mask)[0]

        for i in significant_indices:
            gen_name = self.generators[i].__class__.__name__
            prob = current_probs[i]
            print(f"{gen_name}: {prob:.3f}")
        print("---")
