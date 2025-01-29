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
        blobs = list(bucket.list_blobs(prefix="landsat_images/"))

        total_files = len(blobs)
        total_size = sum(blob.size for blob in blobs if blob.size is not None)

        # Fetch Firestore metrics using Monitoring API
        client = monitoring_v3.MetricServiceClient()
        now = datetime.datetime.utcnow()
        interval = monitoring_v3.TimeInterval(
            {
                "start_time": {"seconds": int((now - datetime.timedelta(days=30)).timestamp())},
                "end_time": {"seconds": int(now.timestamp())},
            }
        )

        # Fetch firestore.googleapis.com/document/read_count
        firestore_reads = 0
        read_query = 'metric.type="firestore.googleapis.com/document/read_count"'
        read_results = client.list_time_series(
            request={
                "name": f"projects/{PROJECT_ID}",
                "filter": read_query,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )

        if read_results:
            for result in read_results:
                for point in result.points:
                    firestore_reads += point.value.int64_value

        # Fetch firestore.googleapis.com/api/request_latencies
        latency_query = 'metric.type="firestore.googleapis.com/api/request_latencies"'
        request_latencies = []
        latency_results = client.list_time_series(
            request={
                "name": f"projects/{PROJECT_ID}",
                "filter": latency_query,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )

        if latency_results:
            for result in latency_results:
                for point in result.points:
                    request_latencies.append(point.value.double_value)

        avg_latency = (
            sum(request_latencies) / len(request_latencies) if request_latencies else 0
        )

        # Fetch firestore.googleapis.com/api/request_count
        request_count = 0
        count_query = 'metric.type="firestore.googleapis.com/api/request_count"'
        count_results = client.list_time_series(
            request={
                "name": f"projects/{PROJECT_ID}",
                "filter": count_query,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )

        if count_results:
            for result in count_results:
                for point in result.points:
                    request_count += point.value.int64_value

        # Build the response
        response_data = {
            "storage": {
                "total_files": total_files,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
            },
            "firestore": {
                "total_reads": firestore_reads,

            },
            "firebase":{
                "average_request_latency_ms": round(avg_latency, 2),
                "total_request_count": request_count,
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
