from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from azure.storage.blob import BlobServiceClient
import requests
from config import AZURE_CONNECTION_STRING, CONTAINER_NAME

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_NASA_DIR = BASE_DIR / "data" / "raw" / "nasa_power"
LOCAL_NASA_DIR.mkdir(parents=True, exist_ok=True)

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


# Full 5 campuses according to UNISOLAR CampusKey
campuses = {
    "Campus_1_Bundoora": {"lat": -37.7214, "lon": 145.0481, "campus_key": 1},
    "Campus_2_Bendigo": {"lat": -36.7865, "lon": 144.2982, "campus_key": 2},
    "Campus_3_Albury": {"lat": -36.1083, "lon": 146.9048, "campus_key": 3},
    "Campus_4_Mildura": {"lat": -34.2045, "lon": 142.1465, "campus_key": 4},
    "Campus_5_Shepparton": {
        "lat": -36.3770,
        "lon": 145.4011,
        "campus_key": 5,
    },
}

API_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
START_DATE = "20200101"
END_DATE = "20220430"
PARAMETERS = "ALLSKY_SFC_SW_DWN,T2M,CLOUD_AMT"

manifest = {
    "source_name": "NASA_POWER_API",
    "source_type": "Semi_Structured_JSON",
    "api_endpoint": API_URL,
    "uploaded_at_utc": datetime.now(timezone.utc).isoformat(),
    "files": {},
}


print("=== STARTING TO DOWNLOAD AND UPLOAD NASA POWER DATA (5 CAMPUSES) TO AZURE ===")

for c_name, meta in campuses.items():
  filename = f"nasa_power_{c_name}.json"
  local_path = LOCAL_NASA_DIR / filename
  blob_path = f"raw/nasa_power/{filename}"

  params = {
      "start": START_DATE,
      "end": END_DATE,
      "latitude": meta["lat"],
      "longitude": meta["lon"],
      "community": "RE",
      "parameters": PARAMETERS,
      "format": "JSON",
  }

  print(
      f"Calling NASA POWER API for {c_name} (CampusKey: {meta['campus_key']}, Lat:"
      f" {meta['lat']}, Lon: {meta['lon']})..."
  )
  res = requests.get(API_URL, params=params, timeout=120)

  if res.status_code == 200:
    with open(local_path, "w", encoding="utf-8") as f:
      f.write(res.text)

    with open(local_path, "rb") as f:
      container_client.get_blob_client(blob_path).upload_blob(
          f, overwrite=True
      )

    manifest["files"][filename] = {
        "campus_key": meta["campus_key"],
        "blob_path": blob_path,
        "size_bytes": os.path.getsize(local_path),
        "md5_checksum": calculate_md5(local_path),
    }
    print(f"-> Successfully downloaded and uploaded: {blob_path}")
  else:
    print(f"-> Error occurred while downloading {c_name}: Status {res.status_code}")

# Save and upload manifest specifically for NASA POWER
manifest_local_path = LOCAL_NASA_DIR / "manifest_nasa.json"
with open(manifest_local_path, "w", encoding="utf-8") as f:
  json.dump(manifest, f, indent=4)

container_client.get_blob_client(
    "raw/nasa_power/manifest_nasa.json"
).upload_blob(open(manifest_local_path, "rb"), overwrite=True)

print("\n Fully completed downloading and uploading NASA POWER data for all 5 campuses to Azure Data Lake!")