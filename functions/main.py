import os
import ee
import requests
import json
from firebase_functions import https_fn
from google.cloud import firestore, storage

# Initialize Google Earth Engine
ee.Initialize()

# Configure Firestore Emulator
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8081"
firestore_client = firestore.Client()

# Configure Google Cloud Storage
os.environ["STORAGE_EMULATOR_HOST"] = "http://127.0.0.1:9199"
BUCKET_NAME = "cloudimagemanager.appspot.com"
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)


def flatten_data(data):
    """Recursively flatten any nested arrays or dictionaries in Firestore data."""
    if isinstance(data, list):
        # Convert nested lists to strings or flatten
        return [",".join(map(str, flatten_data(item))) if isinstance(item, list) else flatten_data(item) for item in data]
    elif isinstance(data, dict):
        # Process nested dictionaries
        return {key: flatten_data(value) for key, value in data.items()}
    else:
        # Return primitive types as-is
        return data


@https_fn.on_request()
def landsat(req: https_fn.Request) -> https_fn.Response:
    try:
        # Retrieve POST data
        data = req.get_json()
        collection_name = data.get("collection", "LANDSAT/LC09/C02/T2_TOA")
        start_date = data.get("start_date", "2022-01-01")
        end_date = data.get("end_date", "2022-02-01")
        region_coordinates = data.get("region", [6.746, 46.529])
        region_radius = data.get("radius", 10000)

        # Define geographic region
        region = ee.Geometry.Point(region_coordinates).buffer(region_radius).bounds()

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

            # Original metadata
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

            # Save metadata in Firestore (original)
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

        # Create an empty collection `landsat_metadata_changed`
        firestore_client.collection("landsat_metadata_changed").document("placeholder").set({})

        # Generate and save manifest_metadata.json in Cloud Storage
        manifest_metadata = {
            "description": "Metadata structure for Landsat images",
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
        manifest_blob = bucket.blob("manifest_metadata.json")
        manifest_blob.upload_from_string(
            json.dumps(manifest_metadata, indent=2), content_type="application/json"
        )

        # Return successful response
        return https_fn.Response(
            json.dumps({
                "message": "Images and metadata processed successfully!",
                "image_count": image_count,
                "saved_images": saved_images,
                "saved_metadata": saved_metadata,
                "manifest_metadata": "manifest_metadata.json saved to Cloud Storage."
            }),
            status=200,
        )

    except Exception as e:
        return https_fn.Response(json.dumps({"error": str(e)}), status=500)
