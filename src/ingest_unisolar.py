from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from azure.storage.blob import BlobServiceClient
from config import AZURE_CONNECTION_STRING, CONTAINER_NAME

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_UNISOLAR_DIR = BASE_DIR / "data" / "raw" / "unisolar"

blob_service_client = BlobServiceClient.from_connection_string(
    AZURE_CONNECTION_STRING
)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)


def calculate_md5(file_path):
  h = hashlib.md5()
  with open(file_path, "rb") as f:
    for chunk in iter(lambda: f.read(4096), b""):
      h.update(chunk)
  return h.hexdigest()


csv_files = [
    "Solar_Energy_Generation.csv",
    "Weather_Data_reordered_all.csv",
    "Solar_Site_Details.csv",
    "Monthly_Summary_Solar.csv",
]

manifest = {
    "source_name": "UNISOLAR_Dataset",
    "source_type": "Structured_CSV",
    "uploaded_at_utc": datetime.now(timezone.utc).isoformat(),
    "files": {},
}


print("=== Uploading UNISOLAR data to Azure Blob Storage ===")
for filename in csv_files:
  local_path = LOCAL_UNISOLAR_DIR / filename
  if local_path.exists():
    blob_path = f"raw/unisolar/{filename}"
    print(f"Uploading {filename} -> {blob_path}...")

    with open(local_path, "rb") as f:
      container_client.get_blob_client(blob_path).upload_blob(
          f, overwrite=True
      )

    manifest["files"][filename] = {
        "blob_path": blob_path,
        "size_bytes": os.path.getsize(local_path),
        "md5_checksum": calculate_md5(local_path),
    }


# Create and upload a separate manifest for unisolar
manifest_local_path = LOCAL_UNISOLAR_DIR / "manifest_unisolar.json"
with open(manifest_local_path, "w", encoding="utf-8") as f:
  json.dump(manifest, f, indent=4)

container_client.get_blob_client(
    "raw/unisolar/manifest_unisolar.json"
).upload_blob(open(manifest_local_path, "rb"), overwrite=True)
print("=== UNISOLAR data upload complete ===")