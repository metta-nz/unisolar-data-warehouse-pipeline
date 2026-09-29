import os
from pathlib import Path
from dotenv import load_dotenv


#define the path to the .env file in the root directory (one level up from src/)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'


# Load the environment variables from the .env file
load_dotenv(dotenv_path=ENV_PATH)


# Get variables from the environment
AZURE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
CONTAINER_NAME = os.getenv('AZURE_CONTAINER_NAME', 'datalake')


# Validate that the Azure Storage connection string is loaded
if not AZURE_CONNECTION_STRING:
  raise ValueError(
      'Error: Can not found AZURE_STORAGE_CONNECTION_STRING in file .env!'
  )