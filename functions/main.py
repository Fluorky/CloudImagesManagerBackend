import os
import ee
import requests
import json
from firebase_functions import https_fn
from google.cloud import storage

# Initialize Google Earth Engine
ee.Initialize()

# Configure Google Cloud Storage
BUCKET_NAME = "cloudimagemanager.firebasestorage.app"  # Replace with your actual bucket name
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

@https_fn.on_request()
def landsat(req: https_fn.Request) -> https_fn.Response:
    try:
        # Retrieve POST request data
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

        # Prepare folders
        images_folder = "landsat_images/"
        metadata_folder = "landsat_metadata/"
        saved_images = []
        saved_metadata = []

        # Process images
        images = collection.toList(image_count)
        for i in range(image_count):
            image = ee.Image(images.get(i))
            raw_metadata = image.getInfo()
            image_id = raw_metadata.get("id").split("/")[-1]

            # Generate thumbnail
            vis_params = {"min": 0.0, "max": 0.4, "bands": ["B4", "B3", "B2"]}
            url = image.getThumbURL({"region": region, "dimensions": 512, "format": "png", **vis_params})

            response = requests.get(url)
            response.raise_for_status()

            # Save image to Cloud Storage
            image_blob_name = f"{images_folder}{image_id}.png"
            bucket.blob(image_blob_name).upload_from_string(response.content, content_type="image/png")
            saved_images.append(image_blob_name)

            # Save metadata
            metadata_blob_name = f"{metadata_folder}{image_id}_metadata.json"
            metadata = {"id": image_id, "properties": raw_metadata.get("properties", {})}
            bucket.blob(metadata_blob_name).upload_from_string(
                json.dumps(metadata, indent=2), content_type="application/json"
            )
            saved_metadata.append(metadata_blob_name)

        # Return response
        return https_fn.Response(
            json.dumps({
                "message": "Images and metadata saved successfully!",
                "image_count": image_count,
                "saved_images": saved_images,
                "saved_metadata": saved_metadata,
            }),
            status=200,
        )
    except Exception as e:
        return https_fn.Response(json.dumps({"error": str(e)}), status=500)
