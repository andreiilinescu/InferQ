from pathlib import Path
import json, hashlib, qiskit.qpy
from pyodbc import Connection
from utils.azure_connection import AzureConnection,sql_safe
from io import BytesIO
import pickle
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
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


def create_circuits_table(conn: Connection,
                          feature_dict: dict[str,str]) -> bool:
    """
    Ensure dbo.circuits exists and contains (at least) the columns mentioned in
    feature_list.  The primary-key column 'qpy_sha256' CHAR(64) is created
    automatically if missing.
    """
    base_cols = {
        "qpy_sha256": "CHAR(64) NOT NULL PRIMARY KEY",
        "blob_path"   : "NVARCHAR(260) NULL",       # path or URL to the .qpy
    }

    cursor = conn.cursor()

    # 1A. Create table skeleton if absent
    if_not_exists = """
    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'circuits' AND schema_id = SCHEMA_ID('dbo'))
    BEGIN
        CREATE TABLE dbo.circuits (
            qpy_sha256 CHAR(64) NOT NULL PRIMARY KEY,
            blob_path    NVARCHAR(260) NULL
        );
    END;
    """
    cursor.execute(if_not_exists)

    # 1B. Fetch existing columns so we don’t re-add them
    cursor.execute("""
        SELECT name
        FROM sys.columns
        WHERE object_id = OBJECT_ID('dbo.circuits');
    """)
    existing_cols = {row[0].lower() for row in cursor.fetchall()}

    # 1C. Add any missing feature columns (default FLOAT NULL)
    for feat, type in feature_dict.items():
        col_name = sql_safe(feat).strip("[]")  
        type= type.upper()    # for existence check only
        if col_name.lower() not in existing_cols:
            alter = f"ALTER TABLE dbo.circuits ADD {sql_safe(col_name)} {type} NULL;"
            cursor.execute(alter)

    conn.commit()
    return True

def save_circuit_metadata(conn: Connection,
                          features: dict[str, any]) -> bool:
    """
    Insert or update one row in dbo.circuits.  features must include:
        * 'qpy_sha256'  – 64-char hex SHA-256 of the circuit blob
        * any/all feature columns and optional 'blob_path'
    All keys are converted to SQL-safe identifiers; unknown columns will
    raise (→ call create_circuits_table first when you add features).
    """
    if "qpy_sha256" not in features:
        raise ValueError("'features' dict must contain 'qpy_sha256'")

    keys, values = zip(*features.items())           # deterministic order
    columns = ", ".join(sql_safe(k) for k in keys)
    placeholders = ", ".join("?" for _ in keys)
    
    # First check if the record exists
    cursor = conn.cursor()
    check_query = "SELECT 1 FROM dbo.circuits WHERE qpy_sha256 = ?"
    cursor.execute(check_query, [features["qpy_sha256"]])
    record_exists = cursor.fetchone() is not None
    
    if record_exists:
        # Update existing record
        set_clauses = ", ".join(f"{sql_safe(k)} = ?" for k in keys if k != "qpy_sha256")
        update_values = [values[i] for i, k in enumerate(keys) if k != "qpy_sha256"]
        update_query = f"UPDATE dbo.circuits SET {set_clauses} WHERE qpy_sha256 = ?"
        update_values.append(features["qpy_sha256"])
        cursor.execute(update_query, update_values)
    else:
        # Insert new record
        insert_query = f"INSERT INTO dbo.circuits ({columns}) VALUES ({placeholders})"
        cursor.execute(insert_query, list(values))
    
    conn.commit()
    return True

from pathlib import PurePosixPath
from azure.storage.blob import BlobServiceClient, ContentSettings
from io import BytesIO

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