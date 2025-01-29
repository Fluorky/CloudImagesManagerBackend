from firebase_functions import https_fn
from google.cloud import storage
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
def get_total_image_size(request: https_fn.Request) -> https_fn.Response:
    """
    Firebase Function to calculate the total size of all images in a specified folder in Firebase Storage.
    """
    try:
        if not BUCKET_NAME:
            return https_fn.Response(
                json.dumps({"error": "Bucket name is not configured in .env"}),
                status=500,
                mimetype="application/json"
            )

        # Connect to the bucket
        bucket = storage_client.bucket(BUCKET_NAME)

        # Define the folder to calculate size
        folder = request.args.get("folder", "landsat_images/")  # Default folder

        # List all blobs in the folder
        blobs = list(bucket.list_blobs(prefix=folder))

        # Calculate thee total size
        total_size = sum(blob.size for blob in blobs if blob.size is not None)

        return https_fn.Response(
            json.dumps({"folder": folder, "total_size_bytes": total_size}),
            status=200,
            mimetype="application/json"
        )

    except Exception as e:
        return https_fn.Response(
            json.dumps({"error": str(e)}),
            status=500,
            mimetype="application/json"
        )
