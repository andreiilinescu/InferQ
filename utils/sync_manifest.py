"""scripts/sync_manifest.py

Synchronise the *local* ``MANIFEST.parquet`` with the canonical copy
stored in the Azure Blob container that hosts all `.qpy` files.

Steps
-----
1.  Download ``MANIFEST.parquet`` from Azure (if it exists).
2.  Load both local and remote manifests into pandas, concatenate, drop
    duplicate ``circuit_id`` rows (keeping the **newest** by
    ``last_modified`` timestamp if available, otherwise preferring the
    local row).
3.  Write the merged manifest back to disk **and** upload it to Azure.
4.  Stage the updated file with Git so you only need to commit & push.

Environment variables
---------------------
* ``AZURE_STORAGE_ACCOUNT``
* **Either** ``AZURE_STORAGE_SAS_TOKEN`` **or** ``AZURE_STORAGE_KEY``

You may also put them in a ``.env`` file—`python-dotenv` is used if
installed.

Usage
-----
```bash
python scripts/sync_manifest.py   # merges & uploads
```
"""

from __future__ import annotations

import os
import pathlib
import sys
from datetime import datetime, timezone
import tempfile

import pandas as pd
from tqdm import tqdm

try:
    from azure.storage.blob import BlobServiceClient  # type: ignore
except ImportError as exc:  # pragma: no cover
    sys.exit(
        "[sync_manifest] ✖  azure-storage-blob not installed.  `uv pip install azure-storage-blob`. "
    )

try:
    from dotenv import load_dotenv  # noqa: F401

    load_dotenv()
except ModuleNotFoundError:
    pass  # .env loading is optional

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCAL_MANIFEST = PROJECT_ROOT / "MANIFEST.parquet"
CONTAINER_NAME = "inferq-dvc"  # same as remote url azure://inferq-dvc
REMOTE_PATH = "MANIFEST.parquet"  # stored at container root

ACC = os.getenv("AZURE_STORAGE_ACCOUNT")
SAS = os.getenv("AZURE_STORAGE_SAS_TOKEN")
KEY = os.getenv("AZURE_STORAGE_KEY")

if not ACC:
    sys.exit("[sync_manifest] ✖  AZURE_STORAGE_ACCOUNT env-var missing")

if not (SAS or KEY):
    sys.exit("[sync_manifest] ✖  Provide AZURE_STORAGE_SAS_TOKEN or AZURE_STORAGE_KEY")

credential = SAS if SAS else KEY
svc_url = f"https://{ACC}.blob.core.windows.net"
service = BlobServiceClient(account_url=svc_url, credential=credential)
container = service.get_container_client(CONTAINER_NAME)

# ----------------------------------------------------------------------------
# Helper: download remote manifest to a temp file (if exists)
# ----------------------------------------------------------------------------
remote_manifest_path: pathlib.Path | None = None
try:
    blob_props = container.get_blob_client(REMOTE_PATH).get_blob_properties()
    remote_manifest_path = pathlib.Path(tempfile.mkstemp(suffix=".parquet")[1])
    with open(remote_manifest_path, "wb") as fh:
        download_stream = container.download_blob(REMOTE_PATH)
        fh.write(download_stream.readall())
    print(
        f"[sync_manifest] ⬇  downloaded remote manifest ({blob_props.size / 1024:.1f} kB)"
    )
except Exception:  # noqa: BLE001
    print("[sync_manifest] ⓘ  remote MANIFEST.parquet not found; will create new one")

# ----------------------------------------------------------------------------
# Load dataframes
# ----------------------------------------------------------------------------
frames: list[pd.DataFrame] = []
print(LOCAL_MANIFEST)
if LOCAL_MANIFEST.exists():
    frames.append(pd.read_parquet(LOCAL_MANIFEST))
    print(f"[sync_manifest] ✓ loaded local manifest with {len(frames[-1])} rows")
else:
    print("[sync_manifest] ⚠  local MANIFEST.parquet missing; will create")

if remote_manifest_path:
    frames.append(pd.read_parquet(remote_manifest_path))
    print(f"[sync_manifest] ✓ loaded remote manifest with {len(frames[-1])} rows")

if not frames:
    sys.exit(
        "[sync_manifest] ✖  no manifest present locally or remotely; nothing to do"
    )

# ----------------------------------------------------------------------------
# Merge – favour newest 'last_modified' or else local
# ----------------------------------------------------------------------------
merged = pd.concat(frames, ignore_index=True)
if "last_modified" not in merged.columns:
    merged["last_modified"] = datetime.now(timezone.utc)

merged.sort_values("last_modified", ascending=False, inplace=True)
merged.drop_duplicates(subset="circuit_id", keep="first", inplace=True)

print(f"[sync_manifest] ⇄ merged → {len(merged)} unique circuits")

# ----------------------------------------------------------------------------
# Save locally
# ----------------------------------------------------------------------------
merged.to_parquet(LOCAL_MANIFEST, compression="snappy")
print(f"[sync_manifest] 💾 wrote {LOCAL_MANIFEST.relative_to(PROJECT_ROOT)}")

# ----------------------------------------------------------------------------
# Upload back to Azure
# ----------------------------------------------------------------------------
print("[sync_manifest] ⬆  uploading merged manifest → Azure …")
with open(LOCAL_MANIFEST, "rb") as fh:
    container.upload_blob(
        name=REMOTE_PATH,
        data=fh,
        overwrite=True,
        content_type="application/octet-stream",
    )
print("[sync_manifest] ✓ upload done")

# ----------------------------------------------------------------------------
# Stage file with Git (optional)
# ----------------------------------------------------------------------------
import subprocess  # noqa: E402  (after azure check)

try:
    subprocess.run(
        ["git", "add", str(LOCAL_MANIFEST.relative_to(PROJECT_ROOT))], check=True
    )
    print(
        "[sync_manifest] ✓ 'git add MANIFEST.parquet' staged – remember to commit & push"
    )
except Exception:  # noqa: BLE001
    print("[sync_manifest] ⚠  could not stage MANIFEST.parquet – is this a Git repo?")
