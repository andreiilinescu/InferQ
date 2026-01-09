from qiskit import transpile
from qiskit.circuit import QuantumCircuit
from qiskit.result import Result
from qiskit_aer import AerSimulator
from typing import Dict, Any, Optional
import numpy as np
from enum import Enum
import logging
import tracemalloc
import time
import numpy as np
import multiprocessing
import queue

try:
    from InfiniQuantumSim.TLtensor import QuantumCircuit as IQSQuantumCircuit, Gate as IQSGate
    import InfiniQuantumSim.mps as iqs_mps
    INFINI_QUANTUM_AVAILABLE = True
except ImportError as e:
    print(f"DEBUG: InfiniQuantumSim import failed: {e}")
    INFINI_QUANTUM_AVAILABLE = False

INFINI_QUANTUM_AVAILABLE=False
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimulationMethod(Enum):
    """Enumeration of available simulation methods in Qiskit"""

    STATEVECTOR = "statevector"
    MPS = "matrix_product_state"
    UNITARY = "unitary"
    DENSITY_MATRIX = "density_matrix"
    STABILIZER = "stabilizer"
    EXTENDED_STABILIZER = "extended_stabilizer"
    AUTOMATIC = "automatic"
    INFINI_QUANTUM = "infiniquantum"


class IQSGateWrapper:
    """Wrapper for InfiniQuantumSim gates"""
    def __init__(self, tensor, qubits):
        self.tensor = tensor
        self.qubits = qubits


def _execute_infiniquantum_simulation(qc, **kwargs):
    """
    Standalone function to run InfiniQuantumSim simulation.
    Can be run in a separate process.
    """
    if not INFINI_QUANTUM_AVAILABLE:
            return {"success": False, "error": "InfiniQuantumSim not installed", "method": "infiniquantum"}
    
    start_time = time.time()
    try:
        # Re-import transpile here to ensure it's available in the process
        from qiskit import transpile
        
        # Transpile to ensure we only have 1 and 2 qubit gates
        # InfiniQuantumSim handles gates by matrix, so we just need to decompose
        transpiled_qc = transpile(qc, basis_gates=['u', 'cx', 'id', 'rz', 'sx', 'x'], optimization_level=2)
        
        num_qubits = transpiled_qc.num_qubits
        
        # Check if circuit is too large for InfiniQuantumSim
        # InfiniQuantumSim uses single characters for indices. 
        # The number of available characters is limited (around 500-600 based on utils.py).
        # Each gate adds 1 or 2 indices.
        # Rough estimate: num_qubits + 2 * num_gates < len(INDICES)
        # If we exceed this, we should skip or fail gracefully.
        from InfiniQuantumSim.utils import INDICES
        # Use a safer estimate or check exact usage if possible.
        # For now, let's be conservative.
        estimated_indices = num_qubits + 3 * len(transpiled_qc.data) # Increased multiplier to be safe
        if estimated_indices >= len(INDICES):
                logger.warning(f"Skipping InfiniQuantumSim: Circuit  too large (indices limit): {estimated_indices} > {len(INDICES)}")
                return {
                "success": False,
                "error": f"Circuit too large for InfiniQuantumSim (indices limit): {estimated_indices} > {len(INDICES)}",
                "method": "infiniquantum",
                "skipped": True
            }

        iqs_qc = IQSQuantumCircuit(num_qubits=num_qubits)
        
        # Add gates to IQS circuit
        for instruction in transpiled_qc.data:
            op = instruction.operation
            qubits = [transpiled_qc.find_bit(q).index for q in instruction.qubits]
            
            if op.name == 'barrier':
                continue
            if op.name == 'measure':
                continue
                
            matrix = op.to_matrix()
            
            # Reshape matrix for IQS Gate
            # IQS expects (2, 2, 2, 2) for 2-qubit gates, (2, 2) for 1-qubit
            if len(qubits) == 1:
                tensor = matrix
            elif len(qubits) == 2:
                tensor = matrix.reshape(2, 2, 2, 2)
            else:
                raise ValueError(f"Unsupported operation {op.name} on {len(qubits)} qubits")
            
            # Create unique name for parameterized gates to avoid tensor collision if needed
            # But for now, let's just use op.name + id(op) to be safe? 
            # Or just op.name if it's standard. 
            # IQS uses name as key in tensor_uniques. 
            # If we have two RZ gates with different angles, they must have different names.
            if len(op.params) > 0:
                gate_name = f"{op.name}_{id(op)}"
            else:
                gate_name = op.name
            
            gate = IQSGate(qubits, tensor, name=gate_name, two_qubit_gate=(len(qubits) == 2))
            iqs_qc.add_gate(gate)

        # Run benchmark
        n_runs = kwargs.get("n_runs", 1)
        # Default to skipping database methods unless explicitly requested
        # This prevents connection errors if DBs are not set up
        oom = kwargs.get("oom", ["psql", "sqlite", "ducksql", "eqc"])
        
        logger.info(f"Running InfiniQuantumSim benchmark with {n_runs} runs...")
        benchmark_results = iqs_qc.benchmark_ciruit_performance(n_runs, oom=oom)
        
        # Process results
        processed_results = {}
        for method, data in benchmark_results.items():
            if not data: # Empty dict if skipped or failed
                continue
                
            # Calculate averages
            if "memory" in data and "time" in data:
                # Check if lists are None (can happen if initialization failed)
                if data["memory"] is None or data["time"] is None:
                    continue

                # Filter out None values which can occur if a run failed
                mem_values = [x for x in data["memory"] if x is not None]
                time_values = [x for x in data["time"] if x is not None]
                
                if mem_values:
                    mem_avg = np.mean(mem_values)
                    mem_avg_mb = mem_avg / (1024 * 1024)
                else:
                    mem_avg_mb = 0.0
                    
                if time_values:
                    tim_avg = np.mean(time_values)
                else:
                    tim_avg = 0.0

                processed_results[method] = {
                    "memory_avg_mb": mem_avg_mb,
                    "time_avg_s": tim_avg,
                    "raw": data
                }
            elif method == "eqc":
                    # Handle EQC special structure if present (based on user snippet)
                    # But user snippet logic was complex, let's just return raw for now
                    processed_results[method] = data

        execution_time = time.time() - start_time
        
        return {
            "success": True,
            "method": "infiniquantum",
            "benchmark_results": processed_results,
            "execution_time": execution_time,
            "backend_name": "InfiniQuantumSim",
        }

    except Exception as e:
        logger.error(f"InfiniQuantumSim failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "method": "infiniquantum",
            "execution_time": time.time() - start_time
        }


def _wrapper_run_iqs(qc, kwargs, q):
    """Wrapper to run IQS simulation in a process and put result in queue"""
    try:
        res = _execute_infiniquantum_simulation(qc, **kwargs)
        q.put(res)
    except Exception as e:
        q.put({"success": False, "error": str(e), "method": "infiniquantum"})


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
        device: str = "CPU",
    ):
        """
        Initialize the quantum simulator.

        Args:
            shots: Number of shots for sampling-based simulations
            seed: Random seed for reproducible results
            timeout_seconds: Maximum time allowed for simulation (in seconds)
            device: Device to run simulations on ("CPU" or "GPU")
        """
        self.shots = shots
        self.seed = seed
        self.timeout_seconds = timeout_seconds
        self.device = device
        self.simulators = {}
        self._initialize_simulators()

    def _initialize_simulators(self):
        """Initialize all available simulators"""
        # Methods that explicitly support GPU
        gpu_methods = {
            SimulationMethod.STATEVECTOR,
            SimulationMethod.DENSITY_MATRIX,
            SimulationMethod.UNITARY,
            SimulationMethod.AUTOMATIC,
        }

        try:
            for method in SimulationMethod:
                if method == SimulationMethod.INFINI_QUANTUM:
                    continue

                # Determine device for this specific method
                method_device = "CPU"
                if self.device == "GPU" and method in gpu_methods:
                    method_device = "GPU"

                self.simulators[method] = AerSimulator(
                    method=method.value,
                    shots=self.shots,
                    seed_simulator=self.seed,
                    device=method_device,
                )
                logger.info(
                    f"Initialized simulator for method {method.value} on device {method_device}"
                )
            
            if INFINI_QUANTUM_AVAILABLE:
                self.simulators[SimulationMethod.INFINI_QUANTUM] = "InfiniQuantumSim"
                logger.info("Initialized InfiniQuantumSim simulator")

            logger.info(f"Initialized {len(self.simulators)} simulators. ")

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
        if method == SimulationMethod.INFINI_QUANTUM:
            return self._run_infiniquantum_simulation(qc, **kwargs)

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
            tracemalloc.start()
            tracemalloc.clear_traces()
            mem_tic, _ = tracemalloc.get_traced_memory()

            start_time = time.time()
            mem_toc = 0

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
                        "skipped": True,
                    }
                else:
                    # Re-raise non-timeout errors
                    raise timeout_error
            finally:
                _, mem_toc = tracemalloc.get_traced_memory()
                tracemalloc.stop()

            measured_memory_mb = (mem_toc - mem_tic) / (1024 * 1024)

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

        if method == SimulationMethod.INFINI_QUANTUM:
            return {
                "method": method.value,
                "name": "InfiniQuantumSim",
                "version": "0.1.0",
                "configuration": {"device": "CPU"}
            }

        simulator = self.simulators[method]
        return {
            "method": method.value,
            "name": simulator.name,
            "version": getattr(simulator, "version", "unknown"),
            "configuration": simulator.configuration().to_dict(),
            "properties": getattr(simulator, "properties", lambda: None)(),
        }

    def _run_infiniquantum_simulation(self, qc: QuantumCircuit, **kwargs) -> Dict[str, Any]:
        """
        Run simulation using InfiniQuantumSim benchmark.
        """
        if not self.timeout_seconds:
            return _execute_infiniquantum_simulation(qc, **kwargs)

        # Run with timeout
        result_queue = multiprocessing.Queue()
        p = multiprocessing.Process(
            target=_wrapper_run_iqs, args=(qc, kwargs, result_queue)
        )
        p.start()
        p.join(self.timeout_seconds)

        if p.is_alive():
            p.terminate()
            p.join()
            logger.warning(f"InfiniQuantumSim simulation timed out after {self.timeout_seconds}s")
            return {
                "success": False,
                "error": f"InfiniQuantumSim timed out after {self.timeout_seconds}s",
                "method": "infiniquantum",
                "skipped": True
            }

        if result_queue.empty():
            logger.warning("InfiniQuantumSim process failed silently")
            return {
                "success": False,
                "error": "InfiniQuantumSim process failed silently",
                "method": "infiniquantum"
            }
            
        return result_queue.get()
