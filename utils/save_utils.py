from pathlib import Path
import json, hashlib, qiskit.qpy


def save_circuit(circuit, features: dict, out_root: Path):
    # Create a temporary file to get the hash first
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        qiskit.qpy.dump(circuit, temp_file)
        temp_path = temp_file.name

    # Calculate hash from the temporary file
    qpy_hash = hashlib.sha256(Path(temp_path).read_bytes()).hexdigest()

    # Use the hash as circuit ID
    cid = qpy_hash
    dir_ = out_root / cid

    # Remove temp file
    Path(temp_path).unlink()

    # Create directory if it doesn't exist, or skip if it does (same circuit)
    try:
        dir_.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(f"⚠️ Circuit {cid} already exists, skipping")
        return cid

    qpy_path = dir_ / "circuit.qpy"
    with open(qpy_path, "wb") as f:
        qiskit.qpy.dump(circuit, f)

    meta = {
        "circuit_id": cid,
        **features,
        "qpy_sha256": qpy_hash,
    }
    with open(dir_ / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"✔ saved {cid}")
    return cid
