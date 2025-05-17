import json, glob, pandas as pd, pathlib, os

manifest_path = pathlib.Path("MANIFEST.parquet")
existing_ids = set()
if manifest_path.exists():
    df = pd.read_parquet(manifest_path, columns=["circuit_id"])
    existing_ids = set(df["circuit_id"].astype(str)) if not df.empty else set()
else:
    df = pd.DataFrame()

rows = []
for meta_path in pathlib.Path("circuits").glob("*/*meta.json"):
    meta = json.loads(meta_path.read_text())
    cid = str(meta.get("circuit_id") or meta_path.parent.name)
    if cid not in existing_ids:
        rows.append(meta)

if rows:
    new_df = pd.DataFrame(rows)
    if manifest_path.exists():
        # Load full manifest to append
        full_df = pd.read_parquet(manifest_path)
        df = pd.concat([full_df, new_df], ignore_index=True)
    else:
        df = new_df
    df.to_parquet(manifest_path, compression="snappy")
    print(f"Appended {len(rows)} new rows. Total manifest rows: {len(df)}")
else:
    print("No new circuits to add. Manifest unchanged.")
