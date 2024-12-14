import os
import ee
import requests
import json
from flask import request, jsonify
from google.cloud import storage
from firebase_functions import https_fn

# Initialize Google Earth Engine
ee.Initialize()

# Configure Firebase Storage Emulator
os.environ["STORAGE_EMULATOR_HOST"] = "http://127.0.0.1:9199"
bucket_name = "cloudimagemanager.appspot.com"  # Ensure this matches your Firebase emulator configuration

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket = storage_client.bucket(bucket_name)


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

        # Fetch Landsat data within the specified date range, collection, and region
        collection = ee.ImageCollection(collection_name) \
            .filterDate(start_date, end_date) \
            .filterBounds(region) \
            .select(['B4', 'B3', 'B2'])

        # Get the number of images in the collection
        image_count = collection.size().getInfo()

        # Prepare folder names
        images_folder = "landsat_images/"
        metadata_folder = "landsat_metadata/"

        saved_images = []
        saved_metadata = []

        # Iterate through images in the collection
        images = collection.toList(image_count)

        for i in range(image_count):
            # Retrieve the image
            image = ee.Image(images.get(i))
            image_id = image.get('system:id').getInfo()

            # Retrieve image metadata
            raw_metadata = image.getInfo()

            # Structure metadata
            metadata = {
                "type": "Image",
                "bands": raw_metadata.get("bands", []),
                "version": raw_metadata.get("version"),
                "id": raw_metadata.get("id"),
                "properties": raw_metadata.get("properties", {})
            }

            vis_params = {
                'min': 0.0,
                'max': 0.4,
                'bands': ['B4', 'B3', 'B2']
            }

            # Generate thumbnail URL for the image
            url = image.getThumbURL({
                'region': region,
                'dimensions': 512,
                'format': 'png',
                **vis_params
            })

            # Fetch the image from the URL
            response = requests.get(url)
            response.raise_for_status()

            # Save the image to Firebase Storage Emulator in the images folder
            image_blob_name = f'{images_folder}landsat_image_{i + 1}.png'
            blob = bucket.blob(image_blob_name)
            blob.upload_from_string(response.content, content_type='image/png')
            saved_images.append(image_blob_name)

            # Save metadata as a JSON file in the metadata folder
            metadata_blob_name = f'{metadata_folder}landsat_image_{i + 1}_metadata.json'
            metadata_blob = bucket.blob(metadata_blob_name)
            metadata_blob.upload_from_string(
                json.dumps(metadata, indent=2), content_type='application/json'
            )
            saved_metadata.append(metadata_blob_name)

        return jsonify({
            "message": "Images and metadata successfully saved to separate folders in the emulator!",
            "image_count": image_count,
            "saved_images": saved_images,
            "saved_metadata": saved_metadata
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
