# Azure Table Storage 
## 📊 **Data Structure**

### Azure Table Storage Schema:
```
Table: circuits
├── PartitionKey: "circuits" (all records in same partition)
├── RowKey: qpy_sha256 (unique circuit hash)
├── Timestamp: Auto-generated
└── Properties:
    ├── num_qubits: int
    ├── circuit_depth: int
    ├── circuit_size: int
    ├── serialization_method: string
    ├── blob_path: string
    └── custom_features: JSON string
```

## 🚀 **Usage Examples**

### Save Circuit Metadata
```python
from utils.azure_connection import AzureConnection
from utils.save_utils import save_circuit_metadata_to_table

azure_conn = AzureConnection()
table_client = azure_conn.get_circuits_table_client()

metadata = {
    "qpy_sha256": "abc123...",
    "num_qubits": 5,
    "circuit_depth": 10,
    "serialization_method": "qpy",
    "custom_features": {"entanglement": 0.75}
}

success = save_circuit_metadata_to_table(table_client, metadata)
```

### Retrieve Circuit Metadata
```python
from utils.save_utils import get_circuit_metadata_from_table

metadata = get_circuit_metadata_from_table(table_client, "abc123...")
if metadata:
    print(f"Circuit has {metadata['num_qubits']} qubits")
```

### List All Circuits
```python
from utils.save_utils import list_circuits_from_table

circuits = list_circuits_from_table(table_client, limit=50)
for circuit in circuits:
    print(f"Hash: {circuit['qpy_sha256']}, Qubits: {circuit['num_qubits']}")
```


## 🧪 **Testing the Setup**

Run the example script to test your Table Storage setup:

```bash
cd utils
python table_storage_example.py
```

This will demonstrate:
- Saving metadata
- Retrieving metadata
- Listing circuits
- Error handling

## 📈 **Performance Considerations**

### Best Practices:
1. **Partition Strategy**: All circuits use the same partition key ("circuits") for simplicity
2. **Row Key Design**: Use circuit hash (qpy_sha256) as row key for uniqueness
3. **Property Limits**: Azure Tables support up to 252 properties per entity
4. **Size Limits**: Each property can be up to 64KB, entity up to 1MB

### Query Patterns:
- **Point Queries**: Fast retrieval by exact hash
- **Range Queries**: Limited to RowKey ranges within a partition
- **Full Scans**: Use list_entities() for browsing all circuits

## 🔍 **Monitoring and Debugging**

### Enable Logging:
```python
import logging
logging.getLogger('azure.data.tables').setLevel(logging.DEBUG)
```

### Common Issues:
1. **Authentication**: Check SAS token permissions and expiry
2. **Property Names**: Ensure property names are valid (no special characters)
3. **Data Types**: Complex objects are automatically JSON-serialized

## 💰 **Cost Comparison**

### Azure SQL Database (Basic Tier):
- ~$5/month minimum
- Additional costs for storage and compute

### Azure Table Storage:
- ~$0.045 per GB/month for storage
- ~$0.0004 per 10,000 transactions
- Significantly cheaper for metadata storage

## 🔧 **Advanced Features**

### Batch Operations:
```python
from azure.data.tables import TableTransactionError

# Batch insert multiple circuits (up to 100 per batch)
batch_operations = []
for metadata in circuit_list:
    entity = prepare_entity(metadata)
    batch_operations.append(("create", entity))

try:
    table_client.submit_transaction(batch_operations)
except TableTransactionError as e:
    print(f"Batch operation failed: {e}")
```

### Conditional Updates:
```python
# Update only if entity hasn't changed
entity = get_circuit_metadata_from_table(table_client, hash_value)
entity["updated_field"] = "new_value"

table_client.update_entity(
    entity, 
    mode="replace",
    etag=entity["etag"],
    match_condition=MatchConditions.IfNotModified
)
```

## 🎯 **Next Steps**

1. **Test the Setup**: Run the example scripts
2. **Migrate Data**: Use the migration script if you have existing SQL data
3. **Update Your Code**: Switch your main application to use Table Storage
4. **Monitor Usage**: Check Azure portal for storage metrics
5. **Optimize**: Adjust partition strategy if needed for your use case

## 📞 **Support**

If you encounter issues:
1. Check the Azure portal for Table Storage metrics
2. Review the logs for detailed error messages
3. Verify SAS token permissions include Tables (not just Blobs)
4. Test with the provided