from qiskit import transpile
from qiskit.circuit import QuantumCircuit
from qiskit.result import Result
from qiskit_aer import AerSimulator
from typing import Dict, Any, Optional
import numpy as np
from enum import Enum
import logging
import psutil
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryMonitor(threading.Thread):
    def __init__(self, interval=0.01):
        super().__init__()
        self.interval = interval
        self.process = psutil.Process()
        self.running = True
        self.max_memory = 0
        self.start_memory = 0

    def run(self):
        try:
            self.start_memory = self.process.memory_info().rss
            self.max_memory = self.start_memory
            while self.running:
                try:
                    mem = self.process.memory_info().rss
                    if mem > self.max_memory:
                        self.max_memory = mem
                except:
                    pass
                time.sleep(self.interval)
        except:
            pass

    def stop(self):
        self.running = False

    def get_peak_memory_mb(self):
        return self.max_memory / (1024 * 1024)


class SimulationMethod(Enum):
    """Enumeration of available simulation methods in Qiskit"""

    STATEVECTOR = "statevector"
    MPS = "matrix_product_state"
    UNITARY = "unitary"
    DENSITY_MATRIX = "density_matrix"
    STABILIZER = "stabilizer"
    EXTENDED_STABILIZER = "extended_stabilizer"
    AUTOMATIC = "automatic"


class QuantumSimulator:
    """
    A comprehensive quantum circuit simulator supporting multiple simulation methods.

    This class provides a unified interface for simulating quantum circuits using
    different backends available in Qiskit, including statevector, MPS, unitary,
    density matrix, stabilizer, and extended stabilizer simulations.
    """

    def __init__(
        self,
        shots: int | None = None,
        seed: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
    ):
        """
        Initialize the quantum simulator.

        Args:
            shots: Number of shots for sampling-based simulations
            seed: Random seed for reproducible results
            timeout_seconds: Maximum time allowed for simulation (in seconds)
        """
        self.shots = shots
        self.seed = seed
        self.timeout_seconds = timeout_seconds
        self.simulators = {}
        self._initialize_simulators()

    def _initialize_simulators(self):
        """Initialize all available simulators"""
        try:
            for method in SimulationMethod:
                self.simulators[method] = AerSimulator(
                    method=method.value, shots=self.shots, seed_simulator=self.seed
                )

            logger.info(f"Initialized {len(self.simulators)} simulators")

        except Exception as e:
            logger.error(f"Error initializing simulators: {e}")
            raise

    def simulate_statevector(self, qc: QuantumCircuit, **kwargs) -> Dict[str, Any]:
        """
        Simulate using the statevector method.

        Args:
            qc: Quantum circuit to simulate
            **kwargs: Additional arguments for the simulator

        Returns:
            Dictionary containing simulation results and metadata
        """
        return self._run_simulation(qc, SimulationMethod.STATEVECTOR, **kwargs)

    def simulate_mps(self, qc: QuantumCircuit, **kwargs) -> Dict[str, Any]:
        """
        Simulate using the Matrix Product State method.

        Args:
            qc: Quantum circuit to simulate
            **kwargs: Additional arguments for the simulator

        Returns:
            Dictionary containing simulation results and metadata
        """
        return self._run_simulation(qc, SimulationMethod.MPS, **kwargs)

    def simulate_unitary(self, qc: QuantumCircuit, **kwargs) -> Dict[str, Any]:
        """
        Simulate using the unitary method.

        Args:
            qc: Quantum circuit to simulate
            **kwargs: Additional arguments for the simulator

        Returns:
            Dictionary containing simulation results and metadata
        """
        return self._run_simulation(qc, SimulationMethod.UNITARY, **kwargs)

    def simulate_density_matrix(self, qc: QuantumCircuit, **kwargs) -> Dict[str, Any]:
        """
        Simulate using the density matrix method.

        Args:
            qc: Quantum circuit to simulate
            **kwargs: Additional arguments for the simulator

        Returns:
            Dictionary containing simulation results and metadata
        """
        return self._run_simulation(qc, SimulationMethod.DENSITY_MATRIX, **kwargs)

    def simulate_stabilizer(self, qc: QuantumCircuit, **kwargs) -> Dict[str, Any]:
        """
        Simulate using the stabilizer method.

        Args:
            qc: Quantum circuit to simulate
            **kwargs: Additional arguments for the simulator

        Returns:
            Dictionary containing simulation results and metadata
        """
        return self._run_simulation(qc, SimulationMethod.STABILIZER, **kwargs)

    def simulate_extended_stabilizer(
        self, qc: QuantumCircuit, **kwargs
    ) -> Dict[str, Any]:
        """
        Simulate using the extended stabilizer method.

        Args:
            qc: Quantum circuit to simulate
            **kwargs: Additional arguments for the simulator

        Returns:
            Dictionary containing simulation results and metadata
        """
        return self._run_simulation(qc, SimulationMethod.EXTENDED_STABILIZER, **kwargs)

    def simulate_auto(self, qc: QuantumCircuit, **kwargs) -> Dict[str, Any]:
        """
        Simulate using the automatic method selector from Qiskit Aer.

        Args:
            qc: Quantum circuit to simulate
            **kwargs: Additional arguments for the simulator

        Returns:
            Dictionary containing simulation results and metadata
        """
        return self._run_simulation(qc, SimulationMethod.AUTOMATIC, **kwargs)

    def simulate_all_methods(
        self, qc: QuantumCircuit, **kwargs
    ) -> Dict[str, Dict[str, Any]]:
        """
        Simulate the circuit using all available methods with size limits.

        Args:
            qc: Quantum circuit to simulate
            **kwargs: Additional arguments for the simulators

        Returns:
            Dictionary mapping method names to their simulation results
        """
        logger.info(
            f"Starting simulation for circuit: {qc.num_qubits} qubits, depth {qc.depth()}, size {qc.size()}"
        )
        results = {}
        successful_methods = 0
        failed_methods = 0

        # Get simulation limits from config
        from config import get_simulation_config

        sim_config = get_simulation_config()
        max_qubits_statevector = sim_config.get("max_qubits_statevector", 20)
        max_qubits_unitary = sim_config.get("max_qubits_unitary", 12)
        max_qubits_mps = sim_config.get("max_qubits_mps", 30)
        max_circuit_size = sim_config.get("max_circuit_size", 1000)

        # Check overall circuit complexity
        if qc.size() > max_circuit_size:
            logger.warning(
                f"Circuit too complex for simulation: {qc.size()} gates > {max_circuit_size} limit"
            )
            # Return failed results for all methods
            failed_result = {
                "success": False,
                "error": f"Circuit too complex: {qc.size()} gates exceeds simulation limit of {max_circuit_size}",
                "skipped": True,
            }
            return {
                method.value: {**failed_result, "method": method.value}
                for method in SimulationMethod
            }

        for method in SimulationMethod:
            try:
                # Check qubit limits before attempting simulation
                skip_reason = None
                if (
                    method == SimulationMethod.STATEVECTOR
                    and qc.num_qubits > max_qubits_statevector
                ):
                    skip_reason = f"Circuit has {qc.num_qubits} qubits, exceeds statevector limit of {max_qubits_statevector}"
                elif (
                    method
                    in [SimulationMethod.UNITARY, SimulationMethod.DENSITY_MATRIX]
                    and qc.num_qubits > max_qubits_unitary
                ):
                    skip_reason = f"Circuit has {qc.num_qubits} qubits, exceeds {method.value} limit of {max_qubits_unitary}"
                elif method == SimulationMethod.MPS and qc.num_qubits > max_qubits_mps:
                    skip_reason = f"Circuit has {qc.num_qubits} qubits, exceeds MPS limit of {max_qubits_mps}"

                if skip_reason:
                    failed_methods += 1
                    logger.warning(
                        f"✗ {method.value} simulation skipped: {skip_reason}"
                    )
                    results[method.value] = {
                        "success": False,
                        "error": skip_reason,
                        "method": method.value,
                        "skipped": True,
                    }
                    continue

                logger.debug(f"Attempting {method.value} simulation...")
                result = self._run_simulation(qc, method, **kwargs)
                results[method.value] = result

                if result.get("success", False):
                    successful_methods += 1
                    logger.info(f"✓ {method.value} simulation completed successfully")
                else:
                    failed_methods += 1
                    logger.warning(
                        f"✗ {method.value} simulation failed: {result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                failed_methods += 1
                logger.warning(
                    f"✗ {method.value} simulation failed with exception: {e}"
                )
                results[method.value] = {
                    "success": False,
                    "error": str(e),
                    "method": method.value,
                }

        # Add additional statevector simulation with save_statevector for entropy/sparsity calculations
        if (
            SimulationMethod.STATEVECTOR in self.simulators
            and qc.num_qubits <= max_qubits_statevector
        ):
            try:
                logger.debug("Attempting statevector_saved simulation...")
                qc_copy = qc.copy()  # Don't modify original circuit
                qc_copy.save_statevector()
                result = self._run_simulation(
                    qc_copy, SimulationMethod.STATEVECTOR, **kwargs
                )
                results["statevector_saved"] = result

                if result.get("success", False):
                    successful_methods += 1
                    logger.info("✓ statevector_saved simulation completed successfully")
                else:
                    failed_methods += 1
                    logger.warning(
                        f"✗ statevector_saved simulation failed: {result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                failed_methods += 1
                logger.warning(
                    f"✗ statevector_saved simulation failed with exception: {e}"
                )
                results["statevector_saved"] = {
                    "success": False,
                    "error": str(e),
                    "method": "statevector_saved",
                }
        elif qc.num_qubits > max_qubits_statevector:
            failed_methods += 1
            results["statevector_saved"] = {
                "success": False,
                "error": f"Circuit has {qc.num_qubits} qubits, exceeds statevector limit of {max_qubits_statevector}",
                "method": "statevector_saved",
                "skipped": True,
            }

        logger.info(
            f"Simulation summary: {successful_methods} successful, {failed_methods} failed out of {len(SimulationMethod) + 1} methods"
        )
        return results

    def _run_simulation(
        self, qc: QuantumCircuit, method: SimulationMethod, **kwargs
    ) -> Dict[str, Any]:
        """
        Internal method to run simulation with specified method.

        Args:
            qc: Quantum circuit to simulate
            method: Simulation method to use
            **kwargs: Additional arguments for the simulator

        Returns:
            Dictionary containing simulation results and metadata
        """
        try:
            simulator = self.simulators[method]
            logger.debug(f"Using simulator: {simulator.name} for {method.value}")

            # Use the circuit directly (parameters should already be assigned during generation)
            circuit_to_simulate = qc

            # Transpile circuit for the specific simulator
            logger.debug(f"Transpiling circuit for {method.value}...")
            transpiled_qc = transpile(circuit_to_simulate, simulator)
            logger.debug(
                f"✓ Circuit transpiled: depth {transpiled_qc.depth()}, size {transpiled_qc.size()}"
            )

            # Run the simulation with timing and timeout handling
            logger.debug(f"Executing {method.value} simulation...")

            # Start memory monitoring
            memory_monitor = MemoryMonitor()
            memory_monitor.start()

            start_time = time.time()

            try:
                # Run simulation with job-level timeout
                job = simulator.run(transpiled_qc, **kwargs)
                result = job.result(timeout=self.timeout_seconds)
                end_time = time.time()
                measured_execution_time = end_time - start_time
                logger.debug(
                    f"✓ {method.value} simulation job completed in {measured_execution_time:.4f}s"
                )
            except Exception as timeout_error:
                end_time = time.time()
                measured_execution_time = end_time - start_time
                if (
                    "timeout" in str(timeout_error).lower()
                    or measured_execution_time >= self.timeout_seconds
                ):
                    timeout_msg = f"Simulation timed out after {measured_execution_time:.1f}s (limit: {self.timeout_seconds}s)"
                    logger.warning(f"✗ {method.value} {timeout_msg}")
                    return {
                        "success": False,
                        "method": method.value,
                        "error": timeout_msg,
                        "execution_time": measured_execution_time,
                    }
                else:
                    # Re-raise non-timeout errors
                    raise timeout_error
            finally:
                memory_monitor.stop()
                memory_monitor.join()

            measured_memory_mb = memory_monitor.get_peak_memory_mb()

            # Extract relevant information based on method
            logger.debug(f"Extracting simulation data for {method.value}...")
            simulation_data = self._extract_simulation_data(
                result, method, transpiled_qc
            )

            # Check if data extraction had errors
            has_extraction_error = "extraction_error" in simulation_data
            if has_extraction_error:
                logger.debug(f"✗ Data extraction had errors for {method.value}")
                success = False
            else:
                logger.debug(f"✓ Data extraction completed for {method.value}")
                success = True

            # Get execution time and memory usage from result if available, fallback to measured time
            execution_time = getattr(
                result,
                "time_taken",
                simulation_data.get("execution_time", measured_execution_time),
            )
            # Prefer measured memory if available, otherwise fallback to result metadata
            memory_usage = (
                measured_memory_mb
                if measured_memory_mb > 0
                else getattr(
                    result, "memory_usage", simulation_data.get("memory_usage")
                )
            )

            # Count transpiled gates by type
            gate_counts = {}
            for instruction in transpiled_qc.data:
                gate_name = instruction.operation.name
                gate_counts[gate_name] = gate_counts.get(gate_name, 0) + 1

            logger.debug(f"Transpiled gate counts for {method.value}: {gate_counts}")

            return {
                "success": success,
                "method": method.value,
                "data": simulation_data,
                # Execution stats
                "execution_time": execution_time,
                "memory_usage": memory_usage,
                # Transpiled circuit stats
                "transpiled_circuit_depth": transpiled_qc.depth(),
                "transpiled_circuit_size": transpiled_qc.size(),
                "transpiled_num_qubits": transpiled_qc.num_qubits,
                "transpiled_num_clbits": transpiled_qc.num_clbits,
                "transpiled_gate_counts": gate_counts,
                "extraction_error": (
                    simulation_data.get("extraction_error")
                    if has_extraction_error
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Simulation failed for method {method.value}: {e}")
            return {"success": False, "method": method.value, "error": str(e)}

    def _extract_simulation_data(
        self, result: Result, method: SimulationMethod, qc: QuantumCircuit
    ) -> Dict[str, Any]:
        """
        Extract minimal simulation data - only counts/simulation data for statevector.
        Returns execution time, memory, and basic stats for all methods.

        Args:
            result: Qiskit Result object
            method: Simulation method used
            qc: Quantum circuit that was simulated

        Returns:
            Dictionary containing minimal extracted data
        """
        data = {}

        try:
            # Try to identify the actual method used
            if (
                hasattr(result, "results")
                and result.results
                and len(result.results) > 0
            ):
                res_metadata = result.results[0].metadata
                if res_metadata and "method" in res_metadata:
                    data["actual_method"] = res_metadata["method"]

            # Only extract detailed simulation data for statevector
            if method == SimulationMethod.STATEVECTOR:
                if "statevector" in result.data(0):
                    probabilities = result.get_statevector().probabilities()
                    # Calculate entropy
                    entropy = self._calculate_entropy(probabilities)
                    # Sparsity
                    sparsity = self._calculate_sparsity(probabilities)

                    data["entropy"] = entropy
                    data["sparsity"] = sparsity
                    data["probabilities"] = probabilities

            # For all other methods, just check if they have counts (if applicable)
            elif hasattr(result, "get_counts") and qc.num_clbits > 0:
                try:
                    data["counts"] = result.get_counts(0)
                except:
                    # If counts extraction fails, don't store anything
                    pass
            metadata = getattr(result, "metadata", None)
            # Basic execution stats for all methods
            data["execution_time"] = getattr(result, "time_taken", None)
            data["memory_usage"] = (
                metadata.get("max_memory_mb", None) if metadata else None
            )

        except Exception as e:
            logger.warning(f"Error extracting data for {method.value}: {e}")
            data["extraction_error"] = str(e)

        return data

    def _calculate_entropy(self, probabilities: np.ndarray) -> float:
        """
        Calculate von Neumann entropy using the existing simulation_utils function.

        Args:
            probabilities: Array of probabilities

        Returns:
            Entropy value
        """
        from .simulation_utils import SimulationAnalyzer

        analyzer = SimulationAnalyzer()
        return analyzer._calculate_entropy(probabilities)

    def _calculate_sparsity(self, probabilities: np.ndarray) -> float:
        """
        Calculates sparsity of a probability distribution.

        Args:
            probabilities: Array of probabilities

        Returns:
            Sparsity value
        """
        from .simulation_utils import SimulationAnalyzer

        analyzer = SimulationAnalyzer()
        return analyzer._calculate_sparsity(probabilities)

    def get_available_methods(self) -> list:
        """
        Get list of available simulation methods.

        Returns:
            List of available simulation method names
        """
        return [method.value for method in SimulationMethod]

    def get_simulator_info(self, method: SimulationMethod) -> Dict[str, Any]:
        """
        Get information about a specific simulator.

        Args:
            method: Simulation method to get info for

        Returns:
            Dictionary containing simulator information
        """
        if method not in self.simulators:
            return {"error": f"Method {method.value} not available"}

        simulator = self.simulators[method]
        return {
            "method": method.value,
            "name": simulator.name,
            "version": getattr(simulator, "version", "unknown"),
            "configuration": simulator.configuration().to_dict(),
            "properties": getattr(simulator, "properties", lambda: None)(),
        }
