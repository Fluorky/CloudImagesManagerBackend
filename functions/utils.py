import json
from datetime import datetime


def get_region_from_cloud_storage(bucket, config_path):
    """Fetch region data from Cloud Storage."""
    try:
        blob = bucket.blob(config_path)
        if not blob.exists():
            raise ValueError(f"Config file not found at gs://{bucket.name}/{config_path}")
        config_data = blob.download_as_text()
        config = json.loads(config_data)
        return config.get("coordinates", [6.746, 46.529]), config.get("radius", 10000)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in config file.")
    except Exception as e:
        raise ValueError(f"Error fetching config: {str(e)}")


def flatten_data(data):
    """Recursively flatten nested arrays or dictionaries in Firestore data."""
    if isinstance(data, list):
        return [",".join(map(str, flatten_data(item))) if isinstance(item, list) else flatten_data(item) for item in
                data]
    elif isinstance(data, dict):
        return {key: flatten_data(value) for key, value in data.items()}
    else:
        return data


def log_error_to_firestore(firestore_client, error_message):
    """Log errors with timestamp to Firestore."""
    if "415" in error_message:
        print(f"Ignoring 415 error: {error_message}")
        return
    try:
        error_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_message": error_message
        }
        firestore_client.collection("error_logs").add(error_log)
    except Exception as e:
        print(f"Failed to log error to Firestore: {e}")
