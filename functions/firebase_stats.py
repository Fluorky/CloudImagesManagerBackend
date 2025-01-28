import os
from firebase_functions import https_fn
from google.cloud import storage
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Firebase Storage client
storage_client = storage.Client()

# Get bucket name from .env
BUCKET_NAME = os.getenv("BUCKET_NAME")


@https_fn.on_request()
def get_firebase_stats(request: https_fn.Request) -> https_fn.Response:
    """
    Firebase Cloud Function to fetch total files and total size from Firebase Storage.
    """
    try:
        if not BUCKET_NAME:
            return https_fn.Response(
                json.dumps({"error": "Bucket name is not configured in .env"}),
                status=500,
                mimetype="application/json",
            )

        # Fetch storage stats
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = list(bucket.list_blobs())

        total_files = len(blobs)
        total_size = sum(blob.size for blob in blobs if blob.size is not None)

        # Build response
        response_data = {
            "storage": {
                "total_files": total_files,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
            }
        }

        return https_fn.Response(
            json.dumps(response_data),
            status=200,
            mimetype="application/json",
        )

    except Exception as e:
        return https_fn.Response(
            json.dumps({"error": f"Unexpected error: {str(e)}"}),
            status=500,
            mimetype="application/json",
        )
