"""
Quantum Circuit Simulation Module

This module provides comprehensive quantum circuit simulation capabilities
using various methods available in Qiskit, including:

- Statevector simulation
- Matrix Product State (MPS) simulation  
- Unitary simulation
- Density matrix simulation
- Stabilizer simulation
- Extended stabilizer simulation
- QASM simulation

Classes:
    QuantumSimulator: Main simulator class supporting all methods
    SimulationAnalyzer: Analysis and comparison utilities
    SimulationMethod: Enumeration of available simulation methods

Functions:
    simulate: Legacy simulation function for backward compatibility
    benchmark_simulation_methods: Comprehensive benchmarking utility
"""

from .simulate import QuantumSimulator, SimulationMethod
from .simulation_utils import SimulationAnalyzer, SimulationMetrics, benchmark_simulation_methods

__all__ = [
    'QuantumSimulator',
    'SimulationMethod', 
    'SimulationAnalyzer',
    'SimulationMetrics',
    'simulate',
    'benchmark_simulation_methods'
]

__version__ = '1.0.0'
__author__ = 'InferQ Team'