import pandas as pd
from azure.data.tables import TableClient
# 💡 IMPORT THIS NEW CLASS
from azure.core.credentials import AzureNamedKeyCredential 
from typing import List, Dict, Any

# --- Configuration (Keep your values here) ---
# using variables from .env file in same directory
from dotenv import load_dotenv
import os
load_dotenv()
STORAGE_ACCOUNT_NAME = os.getenv("STORAGE_ACCOUNT_NAME")
STORAGE_ACCOUNT_KEY = os.getenv("STORAGE_ACCOUNT_KEY")
TABLE_NAME = "circuits"  # Replace with your actual table name
# --- Main Logic ---

def fetch_table_data(account_name: str, account_key: str, table_name: str, row_limit: int = 100) -> List[Dict[str, Any]]:
    """
    Connects to Azure Table Storage, queries a specified number of entities,
    and returns the data as a list of dictionaries.
    """
    print(f"Connecting to table: {table_name}...")
    
    # Construct the endpoint URL
    table_url = f"https://{account_name}.table.core.windows.net"
    
    try:
        # 🟢 THE FIX: Wrap the account key in the required credential object
        credential_object = AzureNamedKeyCredential(
            name=account_name,
            key=account_key
        )
        
        # Create the TableClient using the endpoint and the credential object
        table_client = TableClient(
            endpoint=table_url,
            table_name=table_name,
            credential=credential_object  # <-- Pass the object here!
        )
        
        print(f"Querying the first {row_limit} entities...")
        
        # p_key = "circuits"
        # r_key = "00002c67d57d2eb0a9f99dad03225b2fce0652319b1712044e5bfb2690427039"
        # Query the entities using the generator

        # entity = table_client.get_entity(
        #     partition_key=p_key,
        #     row_key=r_key
        # )
        # getting first entity only
        entities_generator = table_client.query_entities(
            query_filter="",
            top=row_limit
        )
        # # Use a list comprehension to efficiently fetch the top N entities
        entities_list = [dict(entity) for i, entity in enumerate(entities_generator) if i < row_limit]

        print(f"Successfully fetched {len(entities_list)} entities.")
        # print(entities_list)
        # Let us store in a csv file
        df = pd.DataFrame(entities_list)
        df.to_csv(f"{table_name}_data.csv", index=False)
        print(f"Data saved to {table_name}_data.csv")
        return entities_list
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

if __name__ == "__main__":
    fetch_table_data(STORAGE_ACCOUNT_NAME, STORAGE_ACCOUNT_KEY, TABLE_NAME, row_limit=100)