import os
import ee
from google.cloud import firestore, storage
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Initialize Google Earth Engine
ee.Initialize()

# Firestore emulator (for local debugging)
if "FIRESTORE_EMULATOR_HOST" in os.environ:
    os.environ["FIRESTORE_EMULATOR_HOST"] = os.getenv("FIRESTORE_EMULATOR_HOST")
firestore_client = firestore.Client()

# Storage emulator (for local debugging)
if "STORAGE_EMULATOR_HOST" in os.environ:
    os.environ["STORAGE_EMULATOR_HOST"] = os.getenv("STORAGE_EMULATOR_HOST")
storage_client = storage.Client()

# Global configuration
BUCKET_NAME = os.getenv("BUCKET_NAME")
CONFIG_PATH = os.getenv("CONFIG_PATH")
bucket = storage_client.bucket(BUCKET_NAME)
