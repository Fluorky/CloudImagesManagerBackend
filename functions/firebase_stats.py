import os
from firebase_functions import https_fn
from google.cloud import monitoring_v3, storage
import datetime
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize clients
storage_client = storage.Client()

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")


@https_fn.on_request()
def get_firebase_stats(request: https_fn.Request) -> https_fn.Response:
    try:
        if not BUCKET_NAME or not PROJECT_ID:
            return https_fn.Response(
                json.dumps({"error": "Bucket name or project ID is not configured in .env"}),
                status=500,
                mimetype="application/json",
            )

        # Fetch Firebase Storage stats
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = list(bucket.list_blobs())

        total_files = len(blobs)
        total_size = sum(blob.size for blob in blobs if blob.size is not None)

        # Fetch Firestore reads using Monitoring API
        client = monitoring_v3.MetricServiceClient()
        now = datetime.datetime.utcnow()
        interval = monitoring_v3.TimeInterval(
            {
                "start_time": {"seconds": int((now - datetime.timedelta(days=30)).timestamp())},
                "end_time": {"seconds": int(now.timestamp())},
            }
        )
        filter_query = 'metric.type="firestore.googleapis.com/api/request_count"'

        firestore_reads = 0
        results = client.list_time_series(
            request={
                "name": f"projects/{PROJECT_ID}",
                "filter": filter_query,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )

        if results:
            for result in results:
                for point in result.points:
                    firestore_reads += point.value.int64_value

        # Build the response
        response_data = {
            "storage": {
                "total_files": total_files,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
            },
            "firestore": {
                "total_reads": firestore_reads,
            },
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
