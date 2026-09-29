import os
from azure.storage.blob import BlobServiceClient
from config import AZURE_CONNECTION_STRING, CONTAINER_NAME

# Initialize a secure connection without exposing the key in the source code
blob_service_client = BlobServiceClient.from_connection_string(
    AZURE_CONNECTION_STRING
)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)
print(f'Successfully connected to Azure Blob Storage container: {CONTAINER_NAME}')


# List of 5 prefix tiers
tiers = ["raw", "clean", "dq_log", "curated", "logs"]


#create a placeholder file (.keep) to display all 5 folders in Azure Portal
for folder in tiers:
  blob_client = container_client.get_blob_client(f"{folder}/.keep")
  blob_client.upload_blob(b"", overwrite=True)
  print(f"Created virtual folder: {folder}/")

print("Successfully created 5 data lake tiers on Azure!")