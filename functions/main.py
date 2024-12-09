from firebase_functions import https_fn
from firebase_admin import initialize_app
import json
import os
import tarfile
import logging
from usgsxplore.api import API
import dotenv
# Initialize Firebase Admin SDK
initialize_app()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
dotenv.load_dotenv()

# Set up directories
base_dir = os.getcwd()
downloads_dir = os.path.join(base_dir, "downloads")
extracted_dir = os.path.join(base_dir, "extracted")
metadata_dir = os.path.join(base_dir, "metadata")

os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(extracted_dir, exist_ok=True)
os.makedirs(metadata_dir, exist_ok=True)

# USGS API Setup
USGS_USERNAME = os.environ.get("USGS_USERNAME")  # Set your EarthExplorer username in environment variables
USGS_PASSWORD = os.environ.get("USGS_PASSWORD")  # Set your EarthExplorer password in environment variables
api = API(username=USGS_USERNAME, password=USGS_PASSWORD)


def extract_tar_file(input_tar_file_path, extract_to):
    """
    Extracts a tar file to the specified directory.
    """
    try:
        if tarfile.is_tarfile(input_tar_file_path):
            with tarfile.open(input_tar_file_path, "r") as tar:
                tar.extractall(extract_to)
                logger.info(f"Extracted {input_tar_file_path} to {extract_to}")
        else:
            logger.warning(f"File is not a valid tar archive: {input_tar_file_path}")
    except Exception as err:
        logger.error(f"Failed to extract {input_tar_file_path}: {err}")


def save_metadata(metadata, file_path):
    """
    Saves metadata to a JSON file.
    """
    try:
        with open(file_path, "w") as f:
            json.dump(metadata, f, indent=4)
        logger.info(f"Metadata saved to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save metadata to {file_path}: {e}")


def search_and_download(dataset, bounding_box, date_interval, max_results):
    """
    Searches for satellite data and downloads it along with metadata.
    """
    try:
        # Search for satellite data
        logger.info("Searching for satellite data...")
        search_results = api.search(
            dataset=dataset,
            bbox=bounding_box,
            date_interval=date_interval,
            max_results=max_results
        )

        if search_results:
            logger.info(f"Found {len(search_results)} products.")
            for item in search_results:
                entity_id = item["entityId"]
                display_id = item["displayId"]
                logger.info(f"Preparing to download file: {display_id} (ID: {entity_id})")

                # Check download options
                download_options = api.request("download-options", {"datasetName": dataset, "entityIds": [entity_id]})
                if download_options:
                    logger.info(f"Download options available for {entity_id}.")
                    try:
                        # Download the file
                        api.download(dataset=dataset, entity_ids=[entity_id], output_dir=downloads_dir)
                        logger.info(f"Downloaded file for Entity ID: {entity_id}")

                        # Extract the downloaded tar file
                        tar_file_path = os.path.join(downloads_dir, f"{display_id}.tar")
                        extract_path = os.path.join(extracted_dir, display_id)
                        metadata_path = os.path.join(metadata_dir, f"{display_id}.json")

                        if os.path.isfile(tar_file_path):
                            os.makedirs(extract_path, exist_ok=True)
                            extract_tar_file(tar_file_path, extract_path)

                        # Save metadata
                        save_metadata(item, metadata_path)
                    except Exception as e:
                        logger.error(f"Failed to download or extract {display_id}: {e}")
                else:
                    logger.warning(f"No download options available for {entity_id}.")
        else:
            logger.error("No results found for the specified search criteria.")
    finally:
        # Ensure logout from USGS API
        api.logout()
        logger.info("Logged out of the USGS API.")


# Firebase Cloud Function
@https_fn.on_request()
def satellite_data_handler(req: https_fn.Request) -> https_fn.Response:
    """
    Firebase Function to handle satellite data search and download requests.
    """
    try:
        # Parse request JSON
        request_data = req.get_json()
        if not request_data:
            return https_fn.Response("Invalid request, JSON body is required.", status=400)

        # Extract parameters
        dataset = request_data.get("dataset", "landsat_etm_c2_l2")
        bounding_box = request_data.get("bounding_box", [21.0, 52.0, 22.0, 53.0])  # Default bounding box
        date_interval = request_data.get("date_interval", ["2023-01-01", "2023-06-10"])  # Default date interval
        max_results = int(request_data.get("max_results", 4))

        # Ensure bounding_box is a tuple
        bounding_box = tuple(bounding_box)

        # Execute search and download process
        search_and_download(dataset, bounding_box, date_interval, max_results)

        return https_fn.Response("Satellite data processed successfully.", status=200)
    except Exception as e:
        logger.error(f"Error in processing request: {e}")
        return https_fn.Response(f"Error processing request: {e}", status=500)
