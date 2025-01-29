import os
from firebase_functions import https_fn
from google.cloud import monitoring_v3
import datetime
import json
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Fetch project ID and bucket name from environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")


@https_fn.on_request()
def get_network_traffic(request: https_fn.Request) -> https_fn.Response:
    """
    Firebase Function to fetch the 'Sent Bytes' metric for a GCS bucket over a specified date range.
    """
    try:
        # Parse the request payload
        request_data = request.get_json()
        if not request_data:
            return https_fn.Response(
                json.dumps({"error": "Invalid request payload. JSON body is required."}),
                status=400,
                mimetype="application/json",
            )

        start_date_str = request_data.get("start_date")
        end_date_str = request_data.get("end_date")

        # Validate required parameters
        if not start_date_str or not end_date_str:
            return https_fn.Response(
                json.dumps({"error": "Missing required parameters: start_date or end_date."}),
                status=400,
                mimetype="application/json",
            )

        # Parse the dates
        try:
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return https_fn.Response(
                json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."}),
                status=400,
                mimetype="application/json",
            )

        # Define the start and end timestamps
        start_time = datetime.datetime.combine(start_date, datetime.time.min).isoformat() + "Z"
        end_time = datetime.datetime.combine(end_date, datetime.time.max).isoformat() + "Z"

        # Initialize the Monitoring client
        client = monitoring_v3.MetricServiceClient()

        # Build the query to fetch the 'Sent Bytes' metric
        project_name = f"projects/{PROJECT_ID}"
        interval = monitoring_v3.TimeInterval(
            {
                "start_time": start_time,
                "end_time": end_time,
            }
        )
        filter_query = (
            f'metric.type="storage.googleapis.com/network/sent_bytes_count" '
            f'resource.labels.bucket_name="{BUCKET_NAME}"'
        )
        results = client.list_time_series(
            request={
                "name": project_name,
                "filter": filter_query,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )

        # Sum up the total sent bytes
        total_sent_bytes = 0
        for result in results:
            for point in result.points:
                total_sent_bytes += point.value.int64_value

        # Return the total sent bytes
        return https_fn.Response(
            json.dumps(
                {
                    "project_id": PROJECT_ID,
                    "bucket_name": BUCKET_NAME,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "total_sent_bytes": total_sent_bytes,
                }
            ),
            status=200,
            mimetype="application/json",
        )

    except Exception as e:
        return https_fn.Response(
            json.dumps({"error": f"Unexpected error: {str(e)}"}),
            status=500,
            mimetype="application/json",
        )
