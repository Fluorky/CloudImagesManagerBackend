from firebase_functions import https_fn
from google.cloud import logging_v2 as logging
import datetime
import json


@https_fn.on_request()
def get_network_traffic(request: https_fn.Request) -> https_fn.Response:
    """
    Firebase Function to fetch network traffic data for a specified date.
    """
    try:
        # Parse the date from the request
        date_str = request.args.get("date", None)
        if not date_str:
            return https_fn.Response(
                json.dumps({"error": "Date parameter is required (format: YYYY-MM-DD)"}),
                status=400,
                mimetype="application/json"
            )

        # Parse the date
        try:
            target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return https_fn.Response(
                json.dumps({"error": "Invalid date format. Use YYYY-MM-DD"}),
                status=400,
                mimetype="application/json"
            )

        # Set up Google Cloud Logging client
        logging_client = logging.Client()

        # Define the start and end timestamps for the target date
        start_time = datetime.datetime.combine(target_date, datetime.time.min).isoformat() + "Z"
        end_time = datetime.datetime.combine(target_date, datetime.time.max).isoformat() + "Z"

        # Build the log filter
        log_filter = f"""
            resource.type="gcs_bucket"
            timestamp >= "{start_time}"
            timestamp <= "{end_time}"
        """

        # Query logs
        entries = logging_client.list_entries(filter_=log_filter)

        total_traffic = 0
        debug_entries = []  # To collect log data for debugging

        for entry in entries:
            debug_entries.append(entry)  # Collect entries for debugging
            if "protoPayload" in entry.payload:
                payload = entry.payload["protoPayload"]
                if "responseSize" in payload:
                    total_traffic += payload["responseSize"]

        # For debugging purposes, return the raw logs alongside the total traffic
        return https_fn.Response(
            json.dumps({
                "date": date_str,
                "total_traffic_bytes": total_traffic,
                "raw_logs": [entry.to_api_repr() for entry in debug_entries]
            }),
            status=200,
            mimetype="application/json"
        )

    except Exception as e:
        return https_fn.Response(
            json.dumps({"error": str(e)}),
            status=500,
            mimetype="application/json"
        )

