# InferQ Dataset – Contributor Guide (v2)

This README reflects the **current repo layout**
and the **exact commands** you should run every day.

_Python package names, dir structure, and workflow have changed
slightly compared to the first draft._

---

## 0 TL;DR daily loop

```bash
cd inferq-dataset               # repo root (direnv auto‑activates .venv)

git pull                        # get latest code + .dvc pointers
python scripts/sync_manifest.py # merge + pull newest MANIFEST.parquet

# --- add circuits -----------------------------------------------------
python -m generator.build_ghz 256           # or any generator module
python -m generator.build_random 128        # ← module form **required**

# track heavy binaries (.qpy → .dvc pointer)
dvc add circuits/*/circuit.qpy

python generator/build_manifest.py          # refresh local manifest

git add circuits/**/circuit.qpy.dvc \
        circuits/**/meta.json \
        MANIFEST.parquet

git commit -m "Add new circuits"

dvc push                                    # upload blobs → Azure
python scripts/sync_manifest.py             # upload merged manifest

git commit MANIFEST.parquet -m "Sync manifest"
git push
```

---

## 1 Repo anatomy (current)

```
inferq-dataset/
├── generator/             #   • build_ghz.py  (call with  python -m generator.build_ghz)
│   │                      #   • … other generators …
│   └── __init__.py        # makes it a *package* so -m works
├── utils/                 #   • feature_extractors.py  (import paths unchanged)
│   └── __init__.py
├── scripts/
│   └── sync_manifest.py   # merge local+remote MANIFEST.parquet
├── circuits/              # one UUID dir per circuit
│   └── <uuid>/            #   • circuit.qpy      (heavy, ignored by Git)
│                          #   • circuit.qpy.dvc  (pointer, in Git)
│                          #   • meta.json        (tiny, in Git)
├── MANIFEST.parquet       # always tiny; overwritten by sync_script
├── .dvc/                  # DVC config
├── .gitignore             # ignores *.qpy only (not .dvc/.json)
├── .dvcignore             # hides everything *except* circuits/**
└── .envrc                 # direnv loads .env + activates .venv
```

---

## 2 One‑time setup (per machine)

```bash
# install tooling
brew install direnv git-lfs        # or apt/dnf/pacman
uv pip install "dvc[azure]"        # inside any Python 3.12 env

# shell hook
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc   # bash example

# clone
git clone git@github.com:inferq/inferq-dataset.git
cd inferq-dataset
uv venv --python 3.12
source .venv/bin/activate
uv pip sync                     # installs qiskit, pandas, azure libs

direnv allow                    # loads .envrc => credentials + venv
```

Create `.env` (ignored by Git):

```
AZURE_STORAGE_ACCOUNT=inferqstorage
AZURE_STORAGE_SAS_TOKEN=?sv=...
```

---

## 3 Running generators **the right way**

Because `generator/` is a **package**, always invoke modules, e.g.:  
`python -m generator.build_ghz 1000` rather than pointing to the file path.
This guarantees Python adds the project root to `sys.path` so
`import utils.feature_extractors` works.

_(If you really want the shebang style, add `#!/usr/bin/env python` to the
script, `chmod +x`, and call `./generator/build_ghz.py 256`.)_

---

## 4 Workflow details

| Stage                       | Command(s)                           | Notes                      |
| --------------------------- | ------------------------------------ | -------------------------- |
| **Generate circuit(s)**     | `python -m generator...`             | creates `<uuid>/` folders  |
| **Track with DVC**          | `dvc add circuits/*/circuit.qpy`     | writes `.dvc` pointers     |
| **Refresh manifest**        | `python generator/build_manifest.py` | local only                 |
| **Commit light files**      | `git add …` + `git commit`           | `.qpy` _not_ in Git        |
| **Upload heavy blobs**      | `dvc push`                           | to Azure Blob `inferq-dvc` |
| **Merge → upload manifest** | `python scripts/sync_manifest.py`    | overwrites remote copy     |
| **Push code**               | `git push`                           | done                       |

---

## 5 Common pitfalls & fixes

| Error                                               | Fix                                                                          |
| --------------------------------------------------- | ---------------------------------------------------------------------------- |
| `ModuleNotFoundError: utils` when running generator | Use `python -m generator.<name>` from repo root or export `PYTHONPATH=$PWD`. |
| `bad DVC file name … is git‑ignored`                | Edit `.gitignore`: ignore `**/*.qpy` only; keep `.dvc` & `.json`.            |
| `dvc push` 403 forbidden                            | Check `AZURE_STORAGE_SAS_TOKEN` / rotate SAS.                                |

---
