from pathlib import Path
import json, hashlib, qiskit.qpy
from pyodbc import Connection
from utils.azure_connection import AzureConnection,sql_safe

def save_circuit_locally(circuit, features: dict, out_root: Path):
    # Create a temporary file to get the hash first
    buf=BytesIO()
    qiskit.qpy.dump(circuit,buf)
    raw_bytes=buf.getvalue()

    # Calculate hash from the buffer
    qpy_hash = hashlib.sha256(raw_bytes).hexdigest()

    # Use the hash as circuit ID
    cid = qpy_hash
    dir_ = out_root / cid

    

    # Create directory if it doesn't exist, or skip if it does (same circuit)
    try:
        dir_.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(f"⚠️ Circuit {cid} already exists, skipping")
        return cid,{}, False

    qpy_path = dir_ / "circuit.qpy"
    with open(qpy_path, "wb") as f:
        qiskit.qpy.dump(circuit, f)

    meta = {
        "qpy_sha256": qpy_hash,
        **features,
    }
    with open(dir_ / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"✔ saved {cid}")
    return cid, meta, True


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

def upload_circuit_blob(container_client,qc,qpy_sha256:str) -> str:
    """
    Serialise QuantumCircuit qc, upload it to Azure Blob Storage,
    and return the HTTPS URL (suitable for storing in SQL).
    """
    buf=BytesIO()
    qiskit.qpy.dump(qc,buf)
    raw_bytes=buf.getvalue()
    rel_path  = PurePosixPath(qpy_sha256[:2]) / f"{qpy_sha256}.qpy"
    # ---- upload ------------------------------------------------------------
    blob_client = container_client.get_blob_client(str(rel_path))
    blob_client.upload_blob(
        raw_bytes,
        overwrite=True,
        max_concurrency=4,                   # parallel blocks (>4 MiB auto-split)
        content_settings=ContentSettings(
            content_type="application/octet-stream"
        ),
        metadata={                           # optional, handy for quick filters
            "sha256": qpy_sha256,
            "format": "qpy",
            "nqubits": str(qc.num_qubits),
        }
    )
    
    # ---- return a URL that anyone with the SAS or RBAC can read ----------
    return blob_client.url