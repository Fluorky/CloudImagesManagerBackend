import os
import ee
import requests
import json
from firebase_functions import https_fn
from google.cloud import storage, firestore

# Initialize Google Earth Engine
ee.Initialize()

# Configure Google Cloud Storage
os.environ["STORAGE_EMULATOR_HOST"] = "http://127.0.0.1:9199"
BUCKET_NAME = "cloudimagemanager.appspot.com"
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

# Configure Firestore Emulator
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8081"
firestore_client = firestore.Client()


def sanitize_firestore_data(data):
    """
    Sanitize data to ensure compatibility with Firestore.
    This includes flattening nested arrays and removing unsupported types.
    """
    if isinstance(data, list):
        flat_list = []
        for item in data:
            if isinstance(item, list):
                flat_list.extend(sanitize_firestore_data(item))
            else:
                flat_list.append(item)
        return flat_list
    elif isinstance(data, dict):
        sanitized_dict = {}
        for key, value in data.items():
            sanitized_dict[key] = sanitize_firestore_data(value)
        return sanitized_dict
    elif isinstance(data, (str, int, float, bool)):
        return data
    else:
        # Unsupported type for Firestore; return as string for logging
        return str(data)


@https_fn.on_request()
def landsat(req: https_fn.Request) -> https_fn.Response:
    try:
        # Verify content type
        if req.headers.get("Content-Type") != "application/json":
            return https_fn.Response(
                json.dumps({"error": "Content-Type must be 'application/json'"}),
                status=415,
            )

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
        print("Fetching Landsat data...")
        collection = (
            ee.ImageCollection(collection_name)
            .filterDate(start_date, end_date)
            .filterBounds(region)
            .select(["B4", "B3", "B2"])
        )
        image_count = collection.size().getInfo()
        print(f"Total images: {image_count}")

        if image_count == 0:
            return https_fn.Response(json.dumps({"message": "No images found"}), status=404)

        # Folder paths
        images_folder = "landsat_images/"
        batch_size = 5  # Reduced batch size for better memory management

        saved_images = []
        saved_metadata_ids = []

        # Process images in batches
        images = collection.toList(image_count)
        for i in range(0, image_count, batch_size):
            print(f"Processing batch {i // batch_size + 1}...")
            batch = images.slice(i, i + batch_size)
            for j in range(batch.size().getInfo()):
                image = ee.Image(batch.get(j))
                raw_metadata = image.getInfo()
                image_id = raw_metadata.get("id").split("/")[-1]

                # Extract and structure metadata
                properties = raw_metadata.get("properties", {})
                bands = sanitize_firestore_data(raw_metadata.get("bands", []))

                # Prepare metadata
                metadata = {
                    "type": "Image",
                    "id": image_id,
                    "location": {"coordinates": region_coordinates, "region_radius": region_radius},
                    "size": {
                        "width": properties.get("REFLECTIVE_SAMPLES", "Unknown"),
                        "height": properties.get("REFLECTIVE_LINES", "Unknown"),
                    },
                    "acquisition_date": properties.get("DATE_ACQUIRED", "Unknown"),
                    "bands": bands,
                    "properties": sanitize_firestore_data(properties),
                }

                # Debug log: Print metadata before saving
                print("Raw metadata before saving to Firestore:")
                print(json.dumps(metadata, indent=2))

                # Sanitize metadata for Firestore
                metadata = sanitize_firestore_data(metadata)

                # Save metadata to Firestore
                firestore_client.collection("landsat_metadata").document(image_id).set(metadata)
                saved_metadata_ids.append(image_id)

                # Generate thumbnail URL
                vis_params = {"min": 0.0, "max": 0.4, "bands": ["B4", "B3", "B2"]}
                url = image.getThumbURL({"region": region, "dimensions": 256, "format": "png", **vis_params})

                # Download and save image
                response = requests.get(url)
                response.raise_for_status()
                image_blob_name = f"{images_folder}{image_id}.png"
                bucket.blob(image_blob_name).upload_from_string(response.content, content_type="image/png")
                saved_images.append(image_blob_name)

            print(f"Batch {i // batch_size + 1} processed.")

        # Return successful response
        return https_fn.Response(
            json.dumps({
                "message": "Images saved in Storage, metadata saved in Firestore!",
                "image_count": image_count,
                "saved_images": saved_images,
                "saved_metadata_ids": saved_metadata_ids
            }),
            status=200,
        )

    except Exception as e:
        print(f"Error: {str(e)}")
        return https_fn.Response(json.dumps({"error": str(e)}), status=500)
