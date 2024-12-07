import os
import tarfile
import logging
from usgsxplore.api import API
import dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
dotenv.load_dotenv()

USGS_USERNAME = os.environ.get('USGS_USERNAME')  # Set your EarthExplorer username in .env
USGS_PASSWORD = os.environ.get('USGS_PASSWORD')  # Set your EarthExplorer password in .env

# Create necessary directories
base_dir = os.getcwd()
downloads_dir = os.path.join(base_dir, "downloads")
extracted_dir = os.path.join(base_dir, "extracted")
os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(extracted_dir, exist_ok=True)


def extract_tar_file(input_tar_file_path, extract_to):
    """
    Extracts a tar file to the specified directory.
    """
    try:
        if tarfile.is_tarfile(input_tar_file_path):
            with tarfile.open(input_tar_file_path, 'r') as tar:
                tar.extractall(extract_to)
                logger.info(f"Extracted {input_tar_file_path} to {extract_to}")
        else:
            logger.warning(f"File is not a valid tar archive: {input_tar_file_path}")
    except Exception as err:
        logger.error(f"Failed to extract {input_tar_file_path}: {err}")


def search_and_download(dataset, bounding_box, date_interval, max_results):
    """
    Searches for Landsat data and downloads the results.
    """
    # Initialize USGS API
    api = API(username=USGS_USERNAME, password=USGS_PASSWORD)

    try:
        # Search for data
        logger.info("Searching for Landsat satellite data...")
        search_results = api.search(
            dataset=dataset,
            bbox=bounding_box,
            date_interval=date_interval,
            max_results=max_results
        )

        if not search_results:
            logger.error("No results found for the specified search criteria.")
            return

        logger.info(f"Found {len(search_results)} products.")
        for item in search_results:
            entity_id = item["entityId"]
            display_id = item["displayId"]
            logger.info(f"Preparing to download file: {display_id} (ID: {entity_id})")

            # Check download options
            download_options = api.request("download-options", {"datasetName": dataset, "entityIds": [entity_id]})
            if not download_options:
                logger.warning(f"No download options available for {entity_id}.")
                continue

            logger.info(f"Download options available for {entity_id}.")
            try:
                # Download the file
                api.download(dataset=dataset, entity_ids=[entity_id], output_dir=downloads_dir)
                logger.info(f"Downloaded file for Entity ID: {entity_id}")

                # Extract the downloaded tar file
                tar_file_path = os.path.join(downloads_dir, f"{display_id}.tar")
                extract_path = os.path.join(extracted_dir, display_id)

                if os.path.isfile(tar_file_path):
                    os.makedirs(extract_path, exist_ok=True)
                    extract_tar_file(tar_file_path, extract_path)
                else:
                    logger.warning(f"File {tar_file_path} not found for extraction.")
            except Exception as e:
                logger.error(f"Failed to download or extract {display_id}: {e}")

    finally:
        # Ensure logout from USGS API
        api.logout()
        logger.info("Logged out of the USGS API.")


def main():
    """
    Main function to execute the script.
    """
    # Parameters
    dataset = "landsat_etm_c2_l2"  # Example dataset
    bounding_box = (21.0, 52.0, 22.0, 53.0)  # (xmin, ymin, xmax, ymax)
    date_interval = ("2023-01-01", "2023-06-10")  # (start_date, end_date)
    max_results = 4

    # Run the search and download process
    search_and_download(dataset, bounding_box, date_interval, max_results)


if __name__ == "__main__":
    main()
