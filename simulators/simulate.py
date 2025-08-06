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
    
    def __init__(self, shots: int|None = None, seed: Optional[int] = None):
        """
        Initialize the quantum simulator.
        
        Args:
            shots: Number of shots for sampling-based simulations
            seed: Random seed for reproducible results
        """
        self.shots = shots
        self.seed = seed
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
        
        logger.info(f"Simulation summary: {successful_methods} successful, {failed_methods} failed out of {len(SimulationMethod)} methods")
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
            
            # Transpile circuit for the specific simulator
            logger.debug(f"Transpiling circuit for {method.value}...")
            transpiled_qc = transpile(qc, simulator)
            logger.debug(f"✓ Circuit transpiled: depth {transpiled_qc.depth()}, size {transpiled_qc.size()}")
            
            # Run the simulation
            logger.debug(f"Executing {method.value} simulation...")
            job = simulator.run(transpiled_qc, **kwargs)
            result = job.result()
            logger.debug(f"✓ {method.value} simulation job completed")
            
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
            
            return {
                'success': success,
                'method': method.value,
                'result': result,
                'data': simulation_data,
                'circuit_depth': transpiled_qc.depth(),
                'circuit_size': transpiled_qc.size(),
                'num_qubits': transpiled_qc.num_qubits,
                'num_clbits': transpiled_qc.num_clbits,
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
        Extract relevant data from simulation results based on the method used.
        
        Args:
            result: Qiskit Result object
            method: Simulation method used
            qc: Quantum circuit that was simulated
            
        Returns:
            Dictionary containing extracted data
        """
        data = {}
        
        try:
            if method == SimulationMethod.STATEVECTOR:
                if 'statevector' in result.data(0):
                    statevector = result.data(0)['statevector']
                    data['statevector'] = statevector
                    data['probabilities'] = np.abs(statevector) ** 2
                    data['amplitudes'] = statevector
            
            elif method == SimulationMethod.UNITARY:
                if 'unitary' in result.data(0):
                    unitary = result.data(0)['unitary']
                    data['unitary_matrix'] = unitary
                    data['matrix_shape'] = unitary.shape
            
            elif method == SimulationMethod.DENSITY_MATRIX:
                if 'density_matrix' in result.data(0):
                    density_matrix = result.data(0)['density_matrix']
                    data['density_matrix'] = density_matrix
                    data['trace'] = np.trace(density_matrix)
                    data['purity'] = np.trace(density_matrix @ density_matrix).real
            
            elif method in [SimulationMethod.STABILIZER, SimulationMethod.EXTENDED_STABILIZER]:
                if hasattr(result, 'get_counts') and qc.num_clbits > 0:
                    data['counts'] = result.get_counts(0)
                if 'stabilizer' in result.data(0):
                    data['stabilizer_state'] = result.data(0)['stabilizer']
            
            elif method == SimulationMethod.MPS:
                if hasattr(result, 'get_counts') and qc.num_clbits > 0:
                    data['counts'] = result.get_counts(0)
                if 'statevector' in result.data(0):
                    statevector = result.data(0)['statevector']
                    data['statevector'] = statevector
                    data['probabilities'] = np.abs(statevector) ** 2
            
            # Common data for all methods
            data['execution_time'] = getattr(result, 'time_taken', None)
            data['memory_usage'] = getattr(result, 'memory_usage', None)
            
        except Exception as e:
            logger.warning(f"Error extracting data for {method.value}: {e}")
            data['extraction_error'] = str(e)
        
        return data
    
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

