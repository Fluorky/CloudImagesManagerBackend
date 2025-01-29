from firebase_functions import https_fn
from landsat_cron import landsat_cron
from config import firestore_client, bucket
from scaled_image import get_scaled_images
from images_blob_information import get_total_image_size
from network_information import get_network_traffic
from firebase_stats import get_firebase_stats


def initialize_application():
    """
    Perform any necessary application-wide initialization here.
    This might include loading additional configuration,
    setting up logging, or verifying dependencies.
    """
    print("Initializing application...")
    print(f"Firestore Client: {firestore_client}")
    print(f"Storage Bucket: {bucket.name}")


# Initialize the application
initialize_application()

# Register functions for deployment
__all__ = ["landsat_cron", "get_scaled_images", "get_total_image_size", "get_network_traffic", "get_firebase_stats"]  # Explicitly expose the functions for Cloud Functions
