"""
Local storage utilities for quantum circuits.

This module handles saving and loading quantum circuits to/from local filesystem
with multiple serialization formats (QPY, pickle, QASM).
"""

from pathlib import Path
import json
import hashlib
import qiskit.qpy
from io import BytesIO
import pickle
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

def save_circuit_locally(circuit, features: dict, out_root: Path):
    """
    Save a quantum circuit locally with multiple serialization fallbacks.
    
    This function attempts to save circuits using QPY format first, but falls back
    to pickle serialization for very large circuits that exceed QPY limitations.
    """
    
    # Try QPY serialization first
    qpy_success = False
    raw_bytes = None
    serialization_method = "qpy"
    
    try:
        buf = BytesIO()
        qiskit.qpy.dump(circuit, buf)
        raw_bytes = buf.getvalue()
        qpy_success = True
        logger.info("✓ QPY serialization successful")
    except Exception as e:
        logger.warning(f"QPY serialization failed: {e}")
        logger.info("Falling back to pickle serialization...")
        
        # Fallback to pickle serialization
        try:
            buf = BytesIO()
            pickle.dump(circuit, buf)
            raw_bytes = buf.getvalue()
            serialization_method = "pickle"
            logger.info("✓ Pickle serialization successful")
        except Exception as pickle_error:
            logger.error(f"Both QPY and pickle serialization failed: {pickle_error}")
            # Final fallback: create hash from circuit properties
            circuit_str = f"{circuit.num_qubits}_{circuit.depth()}_{circuit.size()}_{str(circuit.data)}"
            raw_bytes = circuit_str.encode('utf-8')
            serialization_method = "metadata"
            logger.info("✓ Using metadata-based hash")

    # Calculate hash from the serialized data
    qpy_hash = hashlib.sha256(raw_bytes).hexdigest()
    cid = qpy_hash
    dir_ = out_root / cid

    # Create directory if it doesn't exist, or skip if it does (same circuit)
    try:
        dir_.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(f"⚠️ Circuit {cid} already exists, skipping")
        return cid, {}, False

    # Save the circuit using the successful method
    if qpy_success:
        # Save as QPY
        qpy_path = dir_ / "circuit.qpy"
        try:
            with open(qpy_path, "wb") as f:
                qiskit.qpy.dump(circuit, f)
            logger.info("✓ Circuit saved in QPY format")
        except Exception as e:
            logger.warning(f"Failed to save QPY file: {e}")
            # Save raw bytes instead
            with open(qpy_path, "wb") as f:
                f.write(raw_bytes)
    elif serialization_method == "pickle":
        # Save as pickle
        pickle_path = dir_ / "circuit.pkl"
        with open(pickle_path, "wb") as f:
            pickle.dump(circuit, f)
        logger.info("✓ Circuit saved in pickle format")
    else:
        # Save circuit as QASM string for metadata method
        qasm_path = dir_ / "circuit.qasm"
        try:
            with open(qasm_path, "w") as f:
                f.write(circuit.qasm())
            logger.info("✓ Circuit saved as QASM")
        except Exception as e:
            logger.warning(f"Failed to save QASM: {e}")
            # Save basic circuit info
            with open(dir_ / "circuit_info.txt", "w") as f:
                f.write(f"Qubits: {circuit.num_qubits}\n")
                f.write(f"Depth: {circuit.depth()}\n")
                f.write(f"Size: {circuit.size()}\n")
                f.write(f"Serialization failed - only metadata available\n")

    # Create comprehensive metadata
    meta = {
        "qpy_sha256": qpy_hash,
        "serialization_method": serialization_method,
        "circuit_qubits": circuit.num_qubits,
        "circuit_depth": circuit.depth(),
        "circuit_size": circuit.size(),
        "qpy_serialization_success": qpy_success,
        **features,
    }
    
    with open(dir_ / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"✔ saved {cid} (method: {serialization_method})")
    return cid, meta, True

def load_circuit_locally(circuit_dir: Path):
    """
    Load a quantum circuit from local storage, handling different serialization formats.
    """
    if not circuit_dir.exists():
        raise FileNotFoundError(f"Circuit directory {circuit_dir} not found")
    
    # Read metadata to determine serialization method
    meta_path = circuit_dir / "meta.json"
    if meta_path.exists():
        with open(meta_path, "r") as f:
            meta = json.load(f)
        serialization_method = meta.get("serialization_method", "qpy")
    else:
        serialization_method = "qpy"  # Default assumption
    
    # Load circuit based on serialization method
    if serialization_method == "qpy":
        qpy_path = circuit_dir / "circuit.qpy"
        if qpy_path.exists():
            try:
                with open(qpy_path, "rb") as f:
                    circuits = qiskit.qpy.load(f)
                return circuits[0] if isinstance(circuits, list) else circuits
            except Exception as e:
                logger.warning(f"Failed to load QPY file: {e}")
    
    elif serialization_method == "pickle":
        pickle_path = circuit_dir / "circuit.pkl"
        if pickle_path.exists():
            with open(pickle_path, "rb") as f:
                return pickle.load(f)
    
    elif serialization_method == "metadata":
        qasm_path = circuit_dir / "circuit.qasm"
        if qasm_path.exists():
            try:
                from qiskit import QuantumCircuit
                return QuantumCircuit.from_qasm_str(open(qasm_path, "r").read())
            except Exception as e:
                logger.warning(f"Failed to load from QASM: {e}")
    
    raise ValueError(f"Could not load circuit from {circuit_dir}")

def get_circuit_info(circuit_dir: Path):
    """
    Get circuit information without loading the full circuit.
    """
    meta_path = circuit_dir / "meta.json"
    if meta_path.exists():
        with open(meta_path, "r") as f:
            return json.load(f)
    return None