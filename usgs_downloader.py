import os
import tarfile
import json
import logging
from datetime import datetime
from usgsxplore.api import API
from PIL import Image
import rasterio
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
    Extracts a tar file to the specified directory and saves metadata in a subfolder.
    """
    try:
        if tarfile.is_tarfile(input_tar_file_path):
            with tarfile.open(input_tar_file_path, 'r') as tar:
                tar.extractall(extract_to)
                logger.info(f"Extracted {input_tar_file_path} to {extract_to}")

                # Create a subfolder for metadata
                metadata_dir = os.path.join(extract_to, "metadata")
                os.makedirs(metadata_dir, exist_ok=True)

                # Process each file and save metadata in the subfolder
                for member in tar.getmembers():
                    file_path = os.path.join(extract_to, member.name)
                    metadata = {
                        "name": member.name,
                        "size": member.size,
                        "modified_time": datetime.fromtimestamp(member.mtime).isoformat() if member.mtime else None,
                        "type": "directory" if member.isdir() else "file"
                    }

                    # If the file is an image, add image-specific metadata
                    if member.isfile():
                        image_metadata = extract_image_metadata(file_path)
                        metadata.update(image_metadata)

                        # Save metadata as a JSON file in the metadata subfolder
                        save_individual_metadata(metadata_dir, member.name, metadata)
    except Exception as err:
        logger.error(f"Failed to extract {input_tar_file_path}: {err}")


def extract_image_metadata(file_path):
    """
    Extracts metadata from image files using PIL and rasterio.
    """
    metadata = {}
    try:
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            with Image.open(file_path) as img:
                metadata = {
                    "image_format": img.format,
                    "image_mode": img.mode,
                    "image_size": img.size,  # (width, height)
                }
        elif file_path.lower().endswith(('.tif', '.tiff')):
            with rasterio.open(file_path) as src:
                metadata = {
                    "crs": src.crs.to_string() if src.crs else None,
                    "bounds": src.bounds,
                    "width": src.width,
                    "height": src.height,
                    "count": src.count,  # Number of bands
                    "transform": src.transform,
                    "driver": src.driver,
                }
    except Exception as err:
        logger.warning(f"Failed to extract image metadata for {file_path}: {err}")
    return metadata


def save_individual_metadata(metadata_dir, file_name, metadata):
    """
    Saves metadata for an individual file as a JSON file in the metadata directory.
    """
    metadata_file_path = os.path.join(metadata_dir, f"{file_name}.json")
    try:
        with open(metadata_file_path, 'w') as f:
            json.dump(metadata, f, indent=4)
        logger.info(f"Saved metadata for {file_name} to {metadata_file_path}")
    except Exception as err:
        logger.error(f"Failed to save metadata for {file_name}: {err}")


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
