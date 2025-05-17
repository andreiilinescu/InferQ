from pathlib import Path
import json, hashlib, uuid, qiskit.qpy


def save_circuit(circuit, features: dict, out_root: Path):
    cid = uuid.uuid4().hex
    dir_ = out_root / cid
    dir_.mkdir(parents=True, exist_ok=False)

    qpy_path = dir_ / "circuit.qpy"
    with open(qpy_path, "wb") as f:
        qiskit.qpy.dump(circuit, f)

    meta = {
        "circuit_id": cid,
        **features,
        "qpy_sha256": hashlib.sha256(qpy_path.read_bytes()).hexdigest(),
    }
    with open(dir_ / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"✔ saved {cid}")
    return cid
