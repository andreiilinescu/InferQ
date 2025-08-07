from typing import List, Union
from qiskit import QuantumCircuit
import random
import numpy as np
import logging

from generators.lib.generator import Generator, BaseParams

# Configure logging
logger = logging.getLogger(__name__)

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
        logger.debug(f"Initializing CircuitMerger with params: {base_params}")
        self.base_params = base_params
        self.generators = self.initialize_generators()
        random.seed(base_params.seed)
        np.random.seed(base_params.seed)
        logger.info(f"CircuitMerger initialized with {len(self.generators)} generators")

    def initialize_generators(self) -> List[Generator]:
        """
        Initialize all generator classes with the base parameters.

        Returns:
            List[Generator]: List of initialized generator instances.
        """
        logger.debug(f"Initializing {len(ALL_GENERATOR_CLASSES)} generator classes...")
        generators = []
        
        for cls in ALL_GENERATOR_CLASSES:
            try:
                generator = cls(self.base_params)
                generators.append(generator)
                logger.debug(f"✓ Initialized {cls.__name__}")
            except Exception as e:
                logger.warning(f"✗ Failed to initialize {cls.__name__}: {e}")
                continue
        
        logger.debug(f"Successfully initialized {len(generators)}/{len(ALL_GENERATOR_CLASSES)} generators")
        return generators

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
            # if step == 0:
            #     print("\nInitial probability distribution:")
            #     self._print_probability_distribution(current_probs, step)

            # Check if we should stop (except for first generator)
            if step > 0 and random.random() < stopping_probability:
                logger.debug(
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

                logger.debug(
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
                logger.debug(f"Updated stopping probability: {stopping_probability:.3f}")
            else:
                # No generators available (shouldn't happen)
                logger.warning("No generators available")
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
        logger.info(f"Starting hierarchical circuit generation...")
        logger.debug(f"Available generators: {len(self.generators)}")
        logger.debug(f"Stopping probability: {stopping_probability}, Max generators: {max_generators}")
        
        if generators_probabilities is None:
            # Equal probability for all generators initially
            generators_probabilities = np.ones(len(self.generators))
            logger.debug("Using equal probabilities for all generators")

        # Select generators based on probability
        logger.debug("Selecting generators based on probability distribution...")
        selected_generators = self.select_generators_by_probability(
            generators_probabilities, stopping_probability, max_generators
        )

        if not selected_generators:
            logger.warning("No generators selected! Returning empty circuit")
            return QuantumCircuit()

        logger.info(f"Selected {len(selected_generators)} generators for hierarchical circuit")
        logger.debug(f"Selected generators: {[gen.__class__.__name__ for gen in selected_generators]}")

        # Generate circuits from selected generators only
        logger.debug("Generating individual circuits from selected generators...")
        successful_circuits = []
        
        for i, generator in enumerate(selected_generators):
            generator_name = generator.__class__.__name__
            logger.debug(f"Processing generator {i+1}/{len(selected_generators)}: {generator_name}")
            
            try:
                logger.debug(f"Generating parameters for {generator_name}...")
                params = generator.generate_parameters()

                logger.debug(f"Generating circuit for {generator_name}...")
                if isinstance(params, tuple):
                    circuit = generator.generate(*params)
                elif isinstance(params, dict):
                    circuit = generator.generate(**params)
                else:
                    circuit = generator.generate(params)

                if circuit is not None and hasattr(circuit, "data"):
                    circuit.name = generator_name
                    successful_circuits.append(circuit)
                    logger.debug(f"✓ Generated {circuit.name}: {circuit.num_qubits}q, depth={circuit.depth()}")
                else:
                    logger.warning(f"✗ {generator_name} returned None or invalid circuit")

            except Exception as e:
                logger.warning(f"✗ Error with {generator_name}: {type(e).__name__}: {e}")
                logger.debug(f"   Full error details: {str(e)}")
                continue

        # Merge the successful circuits
        if not successful_circuits:
            logger.warning("No successful circuits generated! Returning empty circuit")
            return QuantumCircuit()

        logger.info(f"Merging {len(successful_circuits)} successful circuits...")
        
        max_qubits = max(c.num_qubits for c in successful_circuits)
        max_clbits = max(c.num_clbits for c in successful_circuits)
        logger.debug(f"Merged circuit dimensions: {max_qubits} qubits, {max_clbits} clbits")

        merged_circuit = QuantumCircuit(max_qubits, max_clbits)
        merged_circuit.name = f"HierarchicalCircuit_{len(successful_circuits)}gens"

        for i, circuit in enumerate(successful_circuits):
            try:
                logger.debug(f"Composing circuit {i+1}/{len(successful_circuits)}: {circuit.name}")
                
                if i > 0:
                    merged_circuit.barrier()

                # Make parameter names unique to avoid conflicts
                circuit_to_compose = self._make_parameters_unique(circuit, i)

                target_qubits = list(range(min(circuit_to_compose.num_qubits, max_qubits)))
                target_clbits = (
                    list(range(min(circuit_to_compose.num_clbits, max_clbits)))
                    if circuit_to_compose.num_clbits > 0
                    else None
                )

                if target_clbits is not None:
                    merged_circuit.compose(
                        circuit_to_compose,
                        qubits=target_qubits,
                        clbits=target_clbits,
                        inplace=True,
                    )
                else:
                    merged_circuit.compose(circuit_to_compose, qubits=target_qubits, inplace=True)
                
                logger.debug(f"✓ Successfully composed {circuit_to_compose.name}")

            except Exception as e:
                logger.warning(f"✗ Failed to compose {circuit.name}: {e}")
                continue

        logger.info(f"✓ Circuit generation completed: {merged_circuit.num_qubits} qubits, depth {merged_circuit.depth()}, size {merged_circuit.size()}")
        return merged_circuit

    def _make_parameters_unique(self, circuit: QuantumCircuit, circuit_index: int) -> QuantumCircuit:
        """
        Make parameter names unique by adding a circuit index suffix.
        
        Args:
            circuit: The circuit with potentially conflicting parameters
            circuit_index: Index to make parameters unique
            
        Returns:
            Circuit with unique parameter names
        """
        if not circuit.parameters:
            return circuit
            
        # Create a copy of the circuit
        new_circuit = circuit.copy()
        
        # Create parameter mapping with unique names
        parameter_map = {}
        for param in circuit.parameters:
            # Create unique parameter name by adding circuit index
            unique_name = f"{param.name}_c{circuit_index}"
            from qiskit.circuit import Parameter
            new_param = Parameter(unique_name)
            parameter_map[param] = new_param
        
        # Apply parameter mapping
        if parameter_map:
            new_circuit = new_circuit.assign_parameters(parameter_map)
            logger.debug(f"Renamed {len(parameter_map)} parameters for circuit {circuit_index}")
        
        return new_circuit

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

        logger.debug(f"Updating probabilities based on selected: {selected_name}")

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
            logger.debug(
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
        logger.debug(f"\n--- Probability Distribution at Step {step} ---")
        # Use NumPy boolean indexing for efficient filtering
        significant_mask = current_probs > 0.01
        significant_indices = np.where(significant_mask)[0]

        for i in significant_indices:
            gen_name = self.generators[i].__class__.__name__
            prob = current_probs[i]
            logger.debug(f"{gen_name}: {prob:.3f}")
        logger.debug("---")
