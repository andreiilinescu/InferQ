"""
Azure Blob Storage utilities for quantum circuits.

This module handles uploading and downloading quantum circuits to/from
Azure Blob Storage with multiple serialization formats.
"""

import pickle
import logging
from pathlib import PurePosixPath
from azure.storage.blob import ContentSettings
from io import BytesIO
import qiskit.qpy

# Configure logging
logger = logging.getLogger(__name__)

def upload_circuit_blob(container_client, qc, qpy_sha256: str, serialization_method: str = "qpy") -> str:
    """
    Serialize QuantumCircuit qc, upload it to Azure Blob Storage,
    and return the HTTPS URL (suitable for storing in SQL).
    
    Supports multiple serialization methods with fallbacks for large circuits.
    """
    raw_bytes = None
    file_extension = "qpy"
    content_type = "application/octet-stream"
    
    # Try different serialization methods
    if serialization_method == "qpy":
        try:
            buf = BytesIO()
            qiskit.qpy.dump(qc, buf)
            raw_bytes = buf.getvalue()
            file_extension = "qpy"
            logger.info("✓ QPY serialization for upload successful")
        except Exception as e:
            logger.warning(f"QPY serialization for upload failed: {e}")
            serialization_method = "pickle"  # Fallback
    
    if serialization_method == "pickle":
        try:
            buf = BytesIO()
            pickle.dump(qc, buf)
            raw_bytes = buf.getvalue()
            file_extension = "pkl"
            logger.info("✓ Pickle serialization for upload successful")
        except Exception as e:
            logger.warning(f"Pickle serialization for upload failed: {e}")
            serialization_method = "qasm"  # Fallback
    
    if serialization_method == "qasm":
        try:
            qasm_str = qc.qasm()
            raw_bytes = qasm_str.encode('utf-8')
            file_extension = "qasm"
            content_type = "text/plain"
            logger.info("✓ QASM serialization for upload successful")
        except Exception as e:
            logger.error(f"All serialization methods failed: {e}")
            raise ValueError("Unable to serialize circuit for upload")
    
    # Create blob path
    rel_path = PurePosixPath(qpy_sha256[:2]) / f"{qpy_sha256}.{file_extension}"
    
    # Upload to blob storage
    blob_client = container_client.get_blob_client(str(rel_path))
    blob_client.upload_blob(
        raw_bytes,
        overwrite=True,
        max_concurrency=4,  # parallel blocks (>4 MiB auto-split)
        content_settings=ContentSettings(
            content_type=content_type
        ),
        metadata={  # optional, handy for quick filters
            "sha256": qpy_sha256,
            "format": serialization_method,
            "nqubits": str(qc.num_qubits),
            "depth": str(qc.depth()),
            "size": str(qc.size()),
        }
    )
    
    logger.info(f"✓ Circuit uploaded to blob storage (format: {serialization_method})")
    return blob_client.url

def download_circuit_blob(container_client, blob_path: str, serialization_method: str = "qpy"):
    """
    Download and deserialize a quantum circuit from Azure Blob Storage.
    
    Args:
        container_client: Azure container client
        blob_path: Path to the blob in storage
        serialization_method: Method used to serialize the circuit
        
    Returns:
        QuantumCircuit object
    """
    try:
        blob_client = container_client.get_blob_client(blob_path)
        blob_data = blob_client.download_blob().readall()
        
        if serialization_method == "qpy":
            buf = BytesIO(blob_data)
            circuits = qiskit.qpy.load(buf)
            return circuits[0] if isinstance(circuits, list) else circuits
        
        elif serialization_method == "pickle":
            buf = BytesIO(blob_data)
            return pickle.load(buf)
        
        elif serialization_method == "qasm":
            qasm_str = blob_data.decode('utf-8')
            from qiskit import QuantumCircuit
            return QuantumCircuit.from_qasm_str(qasm_str)
        
        else:
            raise ValueError(f"Unsupported serialization method: {serialization_method}")
            
    except Exception as e:
        logger.error(f"Failed to download circuit from blob: {e}")
        raise