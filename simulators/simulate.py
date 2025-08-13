from qiskit import transpile
from qiskit.circuit import QuantumCircuit
from qiskit.result import Result
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector, DensityMatrix, Operator
from typing import Dict, Any, Optional, Union
import numpy as np
from enum import Enum
import logging
from io import BytesIO

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

class QuantumSimulator:
    """
    A comprehensive quantum circuit simulator supporting multiple simulation methods.
    
    This class provides a unified interface for simulating quantum circuits using
    different backends available in Qiskit, including statevector, MPS, unitary,
    density matrix, stabilizer, and extended stabilizer simulations.
    """
    
    def __init__(self, shots: int|None = None, seed: Optional[int] = None, timeout_seconds: Optional[int] = None):
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
                    method=method.value,
                    shots=self.shots,
                    seed_simulator=self.seed
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
    
    def simulate_extended_stabilizer(self, qc: QuantumCircuit, **kwargs) -> Dict[str, Any]:
        """
        Simulate using the extended stabilizer method.
        
        Args:
            qc: Quantum circuit to simulate
            **kwargs: Additional arguments for the simulator
            
        Returns:
            Dictionary containing simulation results and metadata
        """
        return self._run_simulation(qc, SimulationMethod.EXTENDED_STABILIZER, **kwargs)
    
    
    def simulate_all_methods(self, qc: QuantumCircuit, **kwargs) -> Dict[str, Dict[str, Any]]:
        """
        Simulate the circuit using all available methods.
        
        Args:
            qc: Quantum circuit to simulate
            **kwargs: Additional arguments for the simulators
            
        Returns:
            Dictionary mapping method names to their simulation results
        """
        logger.info(f"Starting simulation for circuit: {qc.num_qubits} qubits, depth {qc.depth()}, size {qc.size()}")
        results = {}
        successful_methods = 0
        failed_methods = 0
        
        for method in SimulationMethod:
            try:
                logger.debug(f"Attempting {method.value} simulation...")
                result = self._run_simulation(qc, method, **kwargs)
                results[method.value] = result
                
                if result.get('success', False):
                    successful_methods += 1
                    logger.info(f"✓ {method.value} simulation completed successfully")
                else:
                    failed_methods += 1
                    logger.warning(f"✗ {method.value} simulation failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                failed_methods += 1
                logger.warning(f"✗ {method.value} simulation failed with exception: {e}")
                results[method.value] = {
                    'success': False,
                    'error': str(e),
                    'method': method.value
                }
        
        # Add additional statevector simulation with save_statevector for entropy/sparsity calculations
        if SimulationMethod.STATEVECTOR in self.simulators:
            try:
                logger.debug("Attempting statevector_saved simulation...")
                qc.save_statevector()
                result = self._run_simulation(qc, SimulationMethod.STATEVECTOR, **kwargs)
                results['statevector_saved'] = result
                
                if result.get('success', False):
                    successful_methods += 1
                    logger.info("✓ statevector_saved simulation completed successfully")
                else:
                    failed_methods += 1
                    logger.warning(f"✗ statevector_saved simulation failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                failed_methods += 1
                logger.warning(f"✗ statevector_saved simulation failed with exception: {e}")
                results['statevector_saved'] = {
                    'success': False,
                    'error': str(e),
                    'method': 'statevector_saved'
                }
        
        logger.info(f"Simulation summary: {successful_methods} successful, {failed_methods} failed out of {len(SimulationMethod) + 1} methods")
        return results
    
    def _run_simulation(self, qc: QuantumCircuit, method: SimulationMethod, **kwargs) -> Dict[str, Any]:
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
            logger.debug(f"✓ Circuit transpiled: depth {transpiled_qc.depth()}, size {transpiled_qc.size()}")
            
            # Run the simulation with timing
            logger.debug(f"Executing {method.value} simulation...")
            import time
            start_time = time.time()
            job = simulator.run(transpiled_qc, **kwargs)
            result = job.result(timeout=self.timeout_seconds)
            end_time = time.time()
            measured_execution_time = end_time - start_time
            logger.debug(f"✓ {method.value} simulation job completed in {measured_execution_time:.4f}s")
            
            # Extract relevant information based on method
            logger.debug(f"Extracting simulation data for {method.value}...")
            simulation_data = self._extract_simulation_data(result, method, transpiled_qc)
            
            # Check if data extraction had errors
            has_extraction_error = 'extraction_error' in simulation_data
            if has_extraction_error:
                logger.debug(f"✗ Data extraction had errors for {method.value}")
                success = False
            else:
                logger.debug(f"✓ Data extraction completed for {method.value}")
                success = True
            
            # Get execution time and memory usage from result if available, fallback to measured time
            execution_time = getattr(result, 'time_taken', simulation_data.get('execution_time', measured_execution_time))
            memory_usage = getattr(result, 'memory_usage', simulation_data.get('memory_usage'))
            
            # Count transpiled gates by type
            gate_counts = {}
            for instruction in transpiled_qc.data:
                gate_name = instruction.operation.name
                gate_counts[gate_name] = gate_counts.get(gate_name, 0) + 1
            
            logger.debug(f"Transpiled gate counts for {method.value}: {gate_counts}")
            
            return {
                'success': success,
                'method': method.value,
                'data': simulation_data,
                # Execution stats
                'execution_time': execution_time,
                'memory_usage': memory_usage,
                # Transpiled circuit stats
                'transpiled_circuit_depth': transpiled_qc.depth(),
                'transpiled_circuit_size': transpiled_qc.size(),
                'transpiled_num_qubits': transpiled_qc.num_qubits,
                'transpiled_num_clbits': transpiled_qc.num_clbits,
                'transpiled_gate_counts': gate_counts,
                'extraction_error': simulation_data.get('extraction_error') if has_extraction_error else None
            }
            
        except Exception as e:
            logger.error(f"Simulation failed for method {method.value}: {e}")
            return {
                'success': False,
                'method': method.value,
                'error': str(e)
            }
    
    def _extract_simulation_data(self, result: Result, method: SimulationMethod, qc: QuantumCircuit) -> Dict[str, Any]:
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
            # Only extract detailed simulation data for statevector
            if method == SimulationMethod.STATEVECTOR:
                if 'statevector' in result.data(0):
                    probabilities = result.get_statevector().probabilities()
                    # Calculate entropy
                    entropy = self._calculate_entropy(probabilities)
                    # Sparsity
                    sparsity = self._calculate_sparsity(probabilities)
                    
                    data['entropy'] = entropy
                    data['sparsity'] = sparsity
                    data['probabilities']=probabilities
            
            # For all other methods, just check if they have counts (if applicable)
            elif hasattr(result, 'get_counts') and qc.num_clbits > 0:
                try:
                    data['counts'] = result.get_counts(0)
                except:
                    # If counts extraction fails, don't store anything
                    pass
            metadata=getattr(result, 'metadata', None)
            # Basic execution stats for all methods
            data['execution_time'] = getattr(result, 'time_taken', None)
            data['memory_usage'] =  metadata.get("max_memory_mb",None) if metadata else  None
            
        except Exception as e:
            logger.warning(f"Error extracting data for {method.value}: {e}")
            data['extraction_error'] = str(e)
        
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
            return {'error': f'Method {method.value} not available'}
        
        simulator = self.simulators[method]
        return {
            'method': method.value,
            'name': simulator.name,
            'version': getattr(simulator, 'version', 'unknown'),
            'configuration': simulator.configuration().to_dict(),
            'properties': getattr(simulator, 'properties', lambda: None)()
        }

