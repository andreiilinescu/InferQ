import json, glob, pandas as pd, pathlib

rows = []
for meta_path in pathlib.Path("circuits").glob("*/*meta.json"):
    rows.append(json.loads(meta_path.read_text()))
df = pd.DataFrame(rows)
df.to_parquet("MANIFEST.parquet", compression="snappy")
print("manifest rows:", len(df))
