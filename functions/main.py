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

        # Folder paths
        images_folder = "landsat_images/"
        metadata_folder = "landsat_metadata/"
        changed_metadata_folder = "landsat_metadata_changed/"

        # Create empty folder for changed metadata
        empty_blob = bucket.blob(f"{changed_metadata_folder}/")
        empty_blob.upload_from_string("", content_type="application/x-www-form-urlencoded;charset=UTF-8")

        saved_images = []
        saved_metadata = []

        # Process images
        images = collection.toList(image_count)
        for i in range(image_count):
            image = ee.Image(images.get(i))
            raw_metadata = image.getInfo()
            image_id = raw_metadata.get("id").split("/")[-1]

            # Additional metadata extraction
            properties = raw_metadata.get("properties", {})
            acquisition_date = properties.get("DATE_ACQUIRED", "Unknown")
            size = {
                "width": properties.get("REFLECTIVE_SAMPLES", "Unknown"),
                "height": properties.get("REFLECTIVE_LINES", "Unknown"),
            }
            location = region_coordinates

            # Structure metadata
            metadata = {
                "type": "Image",
                "id": image_id,
                "location": {
                    "coordinates": location,
                    "region_radius": region_radius
                },
                "size": size,
                "acquisition_date": acquisition_date,
                "bands": raw_metadata.get("bands", []),
                "properties": properties,
                "brightness": "auto",
                "contrast": "auto",
                "saturation": "auto",
                "grayscale": False,
                "rotate": 0,
                "flip": {"horizontal": False, "vertical": False},
                "zoom": 1.0
            }

            # Generate thumbnail URL
            vis_params = {"min": 0.0, "max": 0.4, "bands": ["B4", "B3", "B2"]}
            url = image.getThumbURL({"region": region, "dimensions": 512, "format": "png", **vis_params})

            # Download and save image
            response = requests.get(url)
            response.raise_for_status()
            image_blob_name = f"{images_folder}{image_id}.png"
            bucket.blob(image_blob_name).upload_from_string(response.content, content_type="image/png")
            saved_images.append(image_blob_name)

            # Save metadata
            metadata_blob_name = f"{metadata_folder}{image_id}_metadata.json"
            bucket.blob(metadata_blob_name).upload_from_string(
                json.dumps(metadata, indent=2), content_type="application/json"
            )
            saved_metadata.append(metadata_blob_name)

        # Generate manifest_metadata.json
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
                "message": "Images, metadata, and manifest saved successfully!",
                "image_count": image_count,
                "saved_images": saved_images,
                "saved_metadata": saved_metadata,
                "changed_metadata_folder": changed_metadata_folder
            }),
            status=200,
        )

    except Exception as e:
        return https_fn.Response(json.dumps({"error": str(e)}), status=500)