import os
import pyodbc
import struct
from azure import identity
from dotenv import load_dotenv
import re
from azure.storage.blob import ContainerClient

load_dotenv()
sql_connection_string = os.environ["AZURE_SQL_CONNECTIONSTRING"]
container_connection_string=os.environ["AZURE_CONTAINER_SAS_URL"]
PYTYPE_SQLTYPE = {
    int:    "INT",
    float:  "FLOAT",
    bool:   "BIT",
    str:    "NVARCHAR(MAX)",      # long strings
    bytes:  "VARBINARY(MAX)",     # if you ever store blobs inline
}

def sql_safe(name: str) -> str:
    """
    Turn arbitrary feature names into SQL-safe identifiers:  spaces -> _ ,
    parentheses, %, dots, etc. removed; wrapped in [ ] to avoid keyword clashes.
    """
    cleaned = re.sub(r"[^0-9A-Za-z_]", "_", name.strip())
    return f"[{cleaned.lower()}]"

class AzureConnection:
    def __init__(self):
        self.sql_conn=self.create_sql_conn()
        self.container_client=self.create_container_client()
    

    def create_sql_conn(self):
        # credential = identity.DefaultAzureCredential(exclude_interactive_browser_credential=False)
        # token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("UTF-16-LE")
        # token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
        # SQL_COPT_SS_ACCESS_TOKEN = 1256  # This connection option is defined by microsoft in msodbcsql.h
        sql_conn = pyodbc.connect(sql_connection_string)
        return sql_conn
    
    def create_container_client(self)->ContainerClient:
        # Create a blob service client using the SAS token
        # blob_service = BlobServiceClient(account_url=svc_url, credential=SAS)
        container_client = ContainerClient.from_container_url(container_connection_string)
        return container_client
    
    def get_conn(self) -> pyodbc.Connection:
        return self.sql_conn
    
    def get_container_client(self)->ContainerClient:
        return self.container_client