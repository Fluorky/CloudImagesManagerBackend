import os
import ee
import requests
import json
from datetime import datetime, timedelta
from firebase_functions import https_fn
from google.cloud import firestore, storage
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Initialize Google Earth Engine
ee.Initialize()

# Emulators Config

# Firestore emulator (for local debugging)
if "FIRESTORE_EMULATOR_HOST" in os.environ:
    os.environ["FIRESTORE_EMULATOR_HOST"] = os.getenv("FIRESTORE_EMULATOR_HOST")
firestore_client = firestore.Client()

# Storage emulator (for local debugging)
if "STORAGE_EMULATOR_HOST" in os.environ:
    os.environ["STORAGE_EMULATOR_HOST"] = os.getenv("STORAGE_EMULATOR_HOST")

# Cloud Storage bucket and configuration path from .env
BUCKET_NAME = os.getenv("BUCKET_NAME")
CONFIG_PATH = os.getenv("CONFIG_PATH")
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)


def get_region_from_cloud_storage():
    """Fetch region data from Cloud Storage."""
    try:
        blob = bucket.blob(CONFIG_PATH)
        if not blob.exists():
            raise ValueError(f"Config file not found at gs://{BUCKET_NAME}/{CONFIG_PATH}")
        config_data = blob.download_as_text()
        config = json.loads(config_data)
        return config.get("coordinates", [6.746, 46.529]), config.get("radius", 10000)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in config file.")
    except Exception as e:
        raise ValueError(f"Error fetching config: {str(e)}")


def flatten_data(data):
    """Recursively flatten any nested arrays or dictionaries in Firestore data."""
    if isinstance(data, list):
        return [",".join(map(str, flatten_data(item))) if isinstance(item, list) else flatten_data(item) for item in data]
    elif isinstance(data, dict):
        return {key: flatten_data(value) for key, value in data.items()}
    else:
        return data


def log_error_to_firestore(error_message):
    """Log errors with timestamp to Firestore."""
    if "415" in error_message:
        # Skip logging 415 errors
        print(f"Ignoring 415 error: {error_message}")
        return
    try:
        error_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_message": error_message
        }
        firestore_client.collection("error_logs").add(error_log)
    except Exception as e:
        print(f"Failed to log error to Firestore: {e}")


@https_fn.on_request()
def landsat_cron(req: https_fn.Request) -> https_fn.Response:
    try:
        # Get parameters from the request or set defaults
        collection_name = req.get_json().get("collection", "LANDSAT/LC09/C02/T2_TOA")

        # Define current date and calculate date range
        today = datetime.utcnow()
        two_years = timedelta(days=730)  # Two years
        quarter = timedelta(days=90)  # One quarter

        end_date = (today - two_years).date().isoformat()  # Today - quarter
        start_date = (today - two_years - quarter).date().isoformat()  # Today - two years - quarter
        print(end_date)
        print(start_date)

        # Fetch region configuration from Cloud Storage
        region_coordinates, region_radius = get_region_from_cloud_storage()

        # Define geographic region
        region = ee.Geometry.Point(region_coordinates).buffer(region_radius).bounds()
        print(f"Region coordinates: {region_coordinates}")
        print(f"Collection_name{collection_name}")
        # Fetch Landsat data
        collection = (
            ee.ImageCollection(collection_name)
            .filterDate(start_date, end_date)
            .filterBounds(region)
            .select(["B4", "B3", "B2"])
        )

        # Get image count
        image_count = collection.size().getInfo()
        if image_count == 0:
            log_error_to_firestore("No images found")
            return https_fn.Response(json.dumps({"message": "No images found"}), status=404)

        saved_images = []
        saved_metadata = []

        # Process images
        images = collection.toList(image_count)
        for i in range(image_count):
            image = ee.Image(images.get(i))
            raw_metadata = image.getInfo()
            image_id = raw_metadata.get("id").split("/")[-1]

            # Extract additional metadata
            properties = raw_metadata.get("properties", {})
            acquisition_date = properties.get("DATE_ACQUIRED", "Unknown")
            size = {
                "width": properties.get("REFLECTIVE_SAMPLES", "Unknown"),
                "height": properties.get("REFLECTIVE_LINES", "Unknown"),
            }
            location = region_coordinates

            # Process bands
            bands = raw_metadata.get("bands", [])
            if isinstance(bands, list):
                bands = flatten_data(bands)

            # Process properties
            properties = flatten_data(properties)

            # Format metadata
            metadata = {
                "type": "Image",
                "id": image_id,
                "location": {
                    "coordinates": location,
                    "region_radius": region_radius
                },
                "size": size,
                "acquisition_date": acquisition_date,
                "bands": bands,
                "properties": properties,
                "brightness": "auto",
                "contrast": "auto",
                "saturation": "auto",
                "grayscale": False,
                "rotate": 0,
                "flip": {"horizontal": False, "vertical": False},
                "zoom": 1.0
            }

            # Save metadata in Firestore
            firestore_client.collection("landsat_metadata").document(image_id).set(metadata)
            saved_metadata.append(image_id)

            # Generate thumbnail URL
            vis_params = {"min": 0.0, "max": 0.4, "bands": ["B4", "B3", "B2"]}
            url = image.getThumbURL({"region": region, "dimensions": 512, "format": "png", **vis_params})

            # Download and save image in Cloud Storage
            response = requests.get(url)
            response.raise_for_status()
            image_blob_name = f"landsat_images/{image_id}.png"
            bucket.blob(image_blob_name).upload_from_string(response.content, content_type="image/png")
            saved_images.append(image_blob_name)

        # Create empty collection `landsat_metadata_changed` in Firestore
        firestore_client.collection("landsat_metadata_changed").document("placeholder").set({})

        # Generate and save manifest_metadata.json in Cloud Storage
        manifest_metadata = {
            "description": f"Metadata structure for Landsat images from {collection_name}",
            "fields": {
                "type": "Type of data (e.g., Image)",
                "id": "Unique identifier for the image",
                "location": "Geographic location and region radius",
                "size": "Dimensions of the image (width and height)",
                "acquisition_date": "Date the image was acquired",
                "bands": "Information about the image bands",
                "properties": "Additional properties about the image",
                "brightness": "Brightness adjustment (default: auto)",
                "contrast": "Contrast adjustment (default: auto)",
                "saturation": "Saturation adjustment (default: auto)",
                "grayscale": "Boolean indicating if the image is grayscale (default: false)",
                "rotate": "Rotation angle in degrees (default: 0)",
                "flip": {
                    "horizontal": "Boolean indicating horizontal flip (default: false)",
                    "vertical": "Boolean indicating vertical flip (default: false)"
                },
                "zoom": "Zoom factor (default: 1.0)"
            }
        }
        manifest_blob = bucket.blob(f"{collection_name.replace("/", "_")}_manifest_metadata.json")
        manifest_blob.upload_from_string(
            json.dumps(manifest_metadata, indent=2), content_type="application/json"
        )

        # Return successful response
        return https_fn.Response(
            json.dumps({
                "message": f"Cron job executed successfully for collection {collection_name}!",
                "image_count": image_count,
                "saved_images": saved_images,
            }),
            status=200,
        )

    except Exception as e:
        log_error_to_firestore(str(e))
        return https_fn.Response(json.dumps({"error": str(e)}), status=500)
