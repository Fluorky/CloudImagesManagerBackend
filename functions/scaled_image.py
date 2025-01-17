from firebase_functions import https_fn
from google.cloud import storage
from PIL import Image
import io
import os
import json
import base64
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Initialize Cloud Storage client
storage_client = storage.Client()

# Fetch the bucket name from the .env file
BUCKET_NAME = os.getenv("BUCKET_NAME")


@https_fn.on_request()
def get_scaled_images(request: https_fn.Request) -> https_fn.Response:
    """
    Firebase Function endpoint to fetch all images from Google Cloud Storage,
    scale them to HD resolution (720p), and return a list of the scaled images.
    If `save_to_storage` is True, the images will be saved back to Firebase Storage.
    Otherwise, the scaled images are returned as base64 strings.
    """
    try:
        # Parse the JSON request to get optional parameters
        request_data = request.get_json()
        save_to_storage = request_data.get("save_to_storage", False)

        # Ensure BUCKET_NAME is set in the environment variables
        if not BUCKET_NAME:
            return https_fn.Response(
                json.dumps({"error": "Bucket name is not configured in .env"}),
                status=500,
                mimetype="application/json"
            )

        # Connect to the Google Cloud Storage bucket
        bucket = storage_client.bucket(BUCKET_NAME)

        # List all blobs (files) in the "landsat_images" folder
        blobs = list(bucket.list_blobs(prefix="landsat_images/"))

        # If no images are found, return an error response
        if not blobs:
            return https_fn.Response(
                json.dumps({"error": "No images found in the bucket"}),
                status=404,
                mimetype="application/json"
            )

        scaled_images = []

        for blob in blobs:
            # Skip files that do not end with ".png"
            if not blob.name.endswith(".png"):
                continue

            # Download the image data from the bucket
            image_data = blob.download_as_bytes()

            # Open the image using Pillow for processing
            with Image.open(io.BytesIO(image_data)) as img:
                # Resize the image to HD resolution (1280x720)
                resolution = (1280, 720)
                img_resized = img.resize(resolution, Image.Resampling.LANCZOS)

                # Save the resized image to an in-memory file
                output = io.BytesIO()
                img_resized.save(output, format="PNG")
                output.seek(0)

                if save_to_storage:
                    # Upload the scaled image back to Cloud Storage
                    scaled_blob_name = f"scaled_images/{os.path.basename(blob.name)}_hd.png"
                    scaled_blob = bucket.blob(scaled_blob_name)
                    scaled_blob.upload_from_file(output, content_type="image/png")

                # Append the scaled image data to the list (always return base64)
                scaled_images.append(base64.b64encode(output.getvalue()).decode("utf-8"))

        return https_fn.Response(
            json.dumps({"message": "Images scaled successfully", "scaled_images": scaled_images}),
            status=200,
            mimetype="application/json"
        )

    except Exception as e:
        # Handle unexpected errors and return an error response
        return https_fn.Response(
            json.dumps({"error": str(e)}),
            status=500,
            mimetype="application/json"
        )
