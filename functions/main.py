import os
import ee
import requests
from flask import jsonify
from google.cloud import storage
from firebase_functions import https_fn

# Initialize Google Earth Engine
ee.Initialize()

# Firebase Storage Emulator configuration
os.environ["STORAGE_EMULATOR_HOST"] = "http://127.0.0.1:9199"
bucket_name = "cloudimagemanager.appspot.com"  # Ensure this name matches the Firebase emulator configuration

# Initialize GCS client
storage_client = storage.Client()
bucket = storage_client.bucket(bucket_name)


@https_fn.on_request()
def landsat(req: https_fn.Request) -> https_fn.Response:
    try:
        # Define geographic region
        region = ee.Geometry.Point([6.746, 46.529]).buffer(10000).bounds()

        # Fetch Landsat data filtered by date and region
        collection = ee.ImageCollection('LANDSAT/LC09/C02/T2_TOA') \
            .filterDate('2022-01-01', '2022-03-01') \
            .filterBounds(region) \
            .select(['B4', 'B3', 'B2'])

        # Count the number of images in the collection for the region
        image_count = collection.size().getInfo()

        # Prepare to iterate over the images
        images = collection.toList(image_count)
        saved_images = []

        for i in range(image_count):
            # Fetch each image from the collection
            image = ee.Image(images.get(i))
            image_id = image.get('system:id').getInfo()

            vis_params = {
                'min': 0.0,
                'max': 0.4,
                'bands': ['B4', 'B3', 'B2']
            }

            # Generate URL for the image thumbnail
            url = image.getThumbURL({
                'region': region,
                'dimensions': 512,
                'format': 'png',
                **vis_params
            })

            # Fetch the image from the URL
            response = requests.get(url)
            response.raise_for_status()

            # Save the image to Firebase Storage Emulator
            blob_name = f'landsat_image_{i + 1}.png'
            blob = bucket.blob(blob_name)
            blob.upload_from_string(response.content, content_type='image/png')
            saved_images.append(blob_name)

        return jsonify({
            "message": "Images saved successfully in emulator!",
            "image_count": image_count,
            "saved_images": saved_images,
            "region_coordinates": region.getInfo()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
