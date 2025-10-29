# Upload Circuits to Azure

This script uploads all locally stored quantum circuits to Azure Blob Storage and Table Storage.

## Overview

The `upload_circuits_to_azure.py` script:
- 📁 Scans the local `circuits/` directory for circuit data
- 📤 Uploads circuit QPY files to Azure Blob Storage
- 📊 Uploads circuit metadata to Azure Table Storage
- ✅ Handles duplicates (skips already uploaded circuits by default)
- 📈 Shows progress with a progress bar
- 📝 Logs all operations to `upload_circuits_to_azure.log`

## Prerequisites

1. **Azure credentials configured**: Make sure your `.env` file contains:
   ```bash
   AZURE_STORAGE_ACCOUNT=your_account_name
   AZURE_STORAGE_ACCOUNT_KEY=your_account_key  # or
   AZURE_STORAGE_SAS_TOKEN=your_sas_token
   AZURE_CONTAINER_SAS_URL=your_container_url
   ```

2. **Python environment**: Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Upload all circuits (skips already uploaded ones):
```bash
python upload_circuits_to_azure.py
```

### Options

- **Dry run** (simulate without uploading):
  ```bash
  python upload_circuits_to_azure.py --dry-run
  ```

- **Force upload** (overwrite existing circuits):
  ```bash
  python upload_circuits_to_azure.py --force
  ```

- **Custom circuits directory**:
  ```bash
  python upload_circuits_to_azure.py --circuits-dir /path/to/circuits
  ```

- **Verbose logging**:
  ```bash
  python upload_circuits_to_azure.py --verbose
  ```

- **Combine options**:
  ```bash
  python upload_circuits_to_azure.py --dry-run --verbose
  python upload_circuits_to_azure.py --force --circuits-dir ./my_circuits
  ```

### Help

View all available options:
```bash
python upload_circuits_to_azure.py --help
```

## Expected Circuit Directory Structure

Each circuit should be stored in its own directory named by its hash:

```
circuits/
├── 53af0cedfe362e421e68336360c4fe4a1f503a9c1fe01052a92a70088c9f1e0b/
│   ├── circuit.qpy      # QPY serialized circuit
│   └── meta.json        # Circuit metadata
├── abc123.../
│   ├── circuit.qpy
│   └── meta.json
└── ...
```

## What Gets Uploaded

### Blob Storage
- **Location**: `circuits` container (configurable via `AZURE_CONTAINER` env var)
- **Path format**: `{first_2_chars_of_hash}/{hash}.qpy`
- **Example**: `53/53af0cedfe362e421e68336360c4fe4a1f503a9c1fe01052a92a70088c9f1e0b.qpy`
- **Metadata**: Includes circuit properties (num_qubits, depth, size, etc.)

### Table Storage
- **Table name**: `circuits` (configurable via `AZURE_TABLE` env var)
- **Partition key**: `circuits`
- **Row key**: Circuit hash (e.g., `53af0cedfe362e421e68336360c4fe4a1f503a9c1fe01052a92a70088c9f1e0b`)
- **Fields**: All metadata from `meta.json` plus `blob_url`

## Output

The script provides:

1. **Console output**: Real-time progress bar and status messages
2. **Log file**: Detailed log at `upload_circuits_to_azure.log`
3. **Summary statistics**:
   ```
   ================================================================================
   Upload Summary
   ================================================================================
   Total circuits: 150
   Successfully uploaded: 145
   Failed: 2
   Skipped (already exist): 3
   ================================================================================
   ```

## Error Handling

- **Missing files**: Circuits without `circuit.qpy` or `meta.json` are skipped
- **Azure errors**: Connection and upload errors are logged with details
- **Already exists**: By default, circuits already in Azure are skipped (use `--force` to override)
- **Partial failures**: The script continues processing remaining circuits even if some fail

## Examples

### Example 1: Test run before actual upload
```bash
# See what would be uploaded without actually uploading
python upload_circuits_to_azure.py --dry-run --verbose
```

### Example 2: Upload new circuits only
```bash
# Upload only circuits that don't exist in Azure yet
python upload_circuits_to_azure.py
```

### Example 3: Re-upload everything
```bash
# Force re-upload all circuits (overwrites existing)
python upload_circuits_to_azure.py --force --verbose
```

### Example 4: Upload from custom location
```bash
# Upload circuits from a different directory
python upload_circuits_to_azure.py --circuits-dir /backup/circuits
```

## Troubleshooting

### "No circuits found to upload"
- Check that the circuits directory exists and contains circuit subdirectories
- Verify each subdirectory has both `circuit.qpy` and `meta.json`

### "Failed to connect to Azure"
- Verify Azure credentials in your `.env` file
- Check that the storage account name and key/SAS token are correct
- Test Azure connection with `python test-env-scripts/03_test_azure.py`

### "Failed to upload circuit"
- Check Azure storage account permissions
- Verify the container and table exist
- Review the detailed error in `upload_circuits_to_azure.log`

### Slow uploads
- Azure upload speed depends on your internet connection
- Large circuits take longer to upload
- Consider running in batches if you have thousands of circuits

## Related Files

- `utils/blob_storage.py` - Blob storage utilities
- `utils/table_storage.py` - Table storage utilities
- `utils/azure_connection.py` - Azure connection management
- `config.py` - Configuration settings

## Notes

- The script uses QPY serialization format by default (most reliable for Qiskit circuits)
- Progress is saved incrementally - you can interrupt and resume
- The log file is appended to on each run (not overwritten)
- Metadata is automatically enhanced with the blob URL after upload
