import logging
import os
from usgsxplore.api import API
from dotenv import load_dotenv
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Load sensitive data from environment variables
USGS_USERNAME = os.environ.get('USGS_USERNAME')  # Set your EarthExplorer username in environment variables
USGS_PASSWORD = os.environ.get('USGS_PASSWORD')  # Set your EarthExplorer password in environment variables

# Initialize API
api = API(username=USGS_USERNAME, password=USGS_PASSWORD)

# try:
#     # Fetch and list available datasets
#     logger.info("Fetching available datasets...")
#     available_datasets = api.dataset_names()
#     logger.info("Available datasets:")
#     for dataset in available_datasets:
#         print(dataset)
#
# finally:
#     pass
#     api.logout()
#
# # Initialize API
# api = API(username=USGS_USERNAME, password=USGS_PASSWORD)
#
# Search parameters
dataset = "landsat_etm_c2_l2" #"LANDSAT_C2L2"

# Search parameters
# dataset = "LANDSAT_8_C1"
bounding_box = (21.0, 52.0, 22.0, 53.0)  # (xmin, ymin, xmax, ymax)
date_interval = ("2023-01-01", "2023-6-10")  # (start_date, end_date)
max_results = 4

# Create a downloads folder in the current directory
downloads_dir = os.path.join(os.getcwd(), "downloads")
os.makedirs(downloads_dir, exist_ok=True)

# Create an extracted folder in the current directory
extracted_dir = os.path.join(os.getcwd(), "extracted")
os.makedirs(extracted_dir, exist_ok=True)

try:
    logger.info("Searching for Landsat satellite data...")
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

            # Check for download options
            download_options = api.request("download-options", {"datasetName": dataset, "entityIds": [entity_id]})
            if download_options:
                logger.info(f"Download options available for {entity_id}: {download_options}")
                # Attempt download
                try:
                    api.download(dataset=dataset, entity_ids=[entity_id], output_dir=downloads_dir)
                    logger.info(f"File {display_id} downloaded successfully.")
                except Exception as e:
                    logger.error(f"Failed to download {display_id}: {e}")
            else:
                logger.warning(f"No download options available for {entity_id}.")
    else:
        logger.error("No results found for the specified search criteria.")

finally:
    # Ensure to close the session
    api.logout()
    logger.info("Logged out of the USGS API.")