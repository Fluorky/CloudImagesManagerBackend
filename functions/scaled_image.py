from firebase_functions import https_fn
from google.cloud import storage
from PIL import Image
import io
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Initialize Cloud Storage client
storage_client = storage.Client()

# Fetch the bucket name from the .env file
BUCKET_NAME = os.getenv("BUCKET_NAME")

@https_fn.on_request()
def get_scaled_image(request: https_fn.Request) -> https_fn.Response:
    """
    Firebase Function endpoint to fetch and scale an image from Google Cloud Storage to HD resolution (720p).
    """
    try:
        # Parse the JSON request
        request_data = request.get_json()
        if not request_data or "image_id" not in request_data:
            return https_fn.Response(
                json.dumps({"error": "Missing 'image_id' in the request"}),
                status=400,
                mimetype="application/json"
            )

        image_id = request_data["image_id"]

        # Ensure BUCKET_NAME is set
        if not BUCKET_NAME:
            return https_fn.Response(
                json.dumps({"error": "Bucket name is not configured in .env"}),
                status=500,
                mimetype="application/json"
            )

        # Connect to the bucket and fetch the image
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(f"landsat_images/{image_id}.png")

        if not blob.exists():
            return https_fn.Response(
                json.dumps({"error": f"Image {image_id}.png not found in bucket {BUCKET_NAME}"}),
                status=404,
                mimetype="application/json"
            )

        # Download the image as binary data
        image_data = blob.download_as_bytes()

        # Open the image using Pillow
        with Image.open(io.BytesIO(image_data)) as img:
            # Resize the image to HD resolution (1280x720)
            resolution = (1280, 720)
            img_resized = img.resize(resolution, Image.Resampling.LANCZOS)

            # Save resized image to an in-memory file
            output = io.BytesIO()
            img_resized.save(output, format="PNG")
            output.seek(0)

            # Return the image as a response
            return https_fn.Response(
                output.getvalue(),
                status=200,
                mimetype="image/png",
                headers={
                    "Content-Disposition": f"attachment; filename={image_id}_hd.png"
                }
            )

    except Exception as e:
        # Handle unexpected errors
        return https_fn.Response(
            json.dumps({"error": str(e)}),
            status=500,
            mimetype="application/json"
        )
