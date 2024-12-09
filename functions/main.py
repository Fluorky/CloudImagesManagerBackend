from firebase_functions import https_fn
from firebase_admin import initialize_app
import os
import tarfile
import json
import logging
from usgsxplore.api import API
import dotenv

# Initialize Firebase Admin SDK
initialize_app()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
dotenv.load_dotenv()

USGS_USERNAME = os.environ.get("USGS_USERNAME")  # USGS username
USGS_PASSWORD = os.environ.get("USGS_PASSWORD")  # USGS password

# Set up directories
base_dir = os.getcwd()
downloads_dir = os.path.join(base_dir, "downloads")
extracted_dir = os.path.join(base_dir, "extracted")
metadata_dir = os.path.join(base_dir, "metadata")

os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(extracted_dir, exist_ok=True)
os.makedirs(metadata_dir, exist_ok=True)

# Initialize the USGS API
api = API(username=USGS_USERNAME, password=USGS_PASSWORD)


def extract_tar_file(input_tar_file_path, extract_to, metadata_base):
    """
    Extracts a tar file to the specified directory and saves metadata for each file.
    """
    try:
        if tarfile.is_tarfile(input_tar_file_path):
            with tarfile.open(input_tar_file_path, 'r') as tar:
                for member in tar.getmembers():
                    tar.extract(member, extract_to)
                    file_path = os.path.join(extract_to, member.name)
                    file_metadata = {
                        "name": member.name,
                        "size": member.size,
                        "type": "directory" if member.isdir() else "file",
                        "modified_time": member.mtime,
                        "path": file_path
                    }

                    # Save metadata for each file
                    metadata_file_path = os.path.join(metadata_base, f"{member.name}.json")
                    os.makedirs(os.path.dirname(metadata_file_path), exist_ok=True)
                    with open(metadata_file_path, 'w') as meta_file:
                        json.dump(file_metadata, meta_file, indent=4)
                    logger.info(f"Saved metadata for {member.name} to {metadata_file_path}")
        else:
            logger.warning(f"File is not a valid tar archive: {input_tar_file_path}")
    except Exception as err:
        logger.error(f"Failed to extract {input_tar_file_path}: {err}")


@https_fn.on_request()
def search_and_download(req: https_fn.Request) -> https_fn.Response:
    """
    Firebase HTTP Function to search Landsat data, download results,
    extract files, and save metadata for each file.
    """
    try:
        # Parse the request data
        data = req.get_json()
        if not data:
            return https_fn.Response("Invalid request, JSON body is required.", status=400)

        dataset = data.get('dataset', 'landsat_etm_c2_l2')
        bounding_box = data.get('bounding_box', [21.0, 52.0, 22.0, 53.0])
        date_interval = data.get('date_interval', ['2023-01-01', '2023-06-10'])
        max_results = data.get('max_results', 4)

        logger.info("Starting Landsat data search...")
        search_results = api.search(
            dataset=dataset,
            bbox=bounding_box,
            date_interval=date_interval,
            max_results=max_results
        )

        if not search_results:
            logger.info("No results found for the given search criteria.")
            return https_fn.Response(
                json.dumps({"status": "success", "message": "No search results found"}),
                status=200,
                headers={"Content-Type": "application/json"}
            )

        logger.info(f"Found {len(search_results)} products.")

        results = []
        for item in search_results:
            entity_id = item["entityId"]
            display_id = item["displayId"]
            logger.info(f"Preparing to download file: {display_id} (ID: {entity_id})")

            # Get download options
            download_options = api.request("download-options", {"datasetName": dataset, "entityIds": [entity_id]})
            if not download_options:
                logger.warning(f"No download options available for {entity_id}.")
                continue

            try:
                # Download the file
                api.download(dataset=dataset, entity_ids=[entity_id], output_dir=downloads_dir)
                logger.info(f"Downloaded file for ID: {entity_id}")

                # Extract the downloaded tar file
                tar_file_path = os.path.join(downloads_dir, f"{display_id}.tar")
                extract_path = os.path.join(extracted_dir, display_id)
                file_metadata_dir = os.path.join(metadata_dir, display_id)

                if os.path.isfile(tar_file_path):
                    os.makedirs(extract_path, exist_ok=True)
                    os.makedirs(file_metadata_dir, exist_ok=True)
                    extract_tar_file(tar_file_path, extract_path, file_metadata_dir)

                    results.append({
                        "entity_id": entity_id,
                        "display_id": display_id,
                        "download_path": tar_file_path,
                        "extract_path": extract_path,
                        "metadata_path": file_metadata_dir
                    })
                else:
                    logger.warning(f"File {tar_file_path} not found or is not a tar file.")
            except Exception as e:
                logger.error(f"Failed to download or extract {display_id}: {e}")
                continue

        return https_fn.Response(
            json.dumps({"status": "success", "results": results}),
            status=200,
            headers={"Content-Type": "application/json"}
        )

    except Exception as e:
        logger.error(f"Error during processing: {e}")
        return https_fn.Response(
            json.dumps({"status": "error", "message": str(e)}),
            status=500,
            headers={"Content-Type": "application/json"}
        )

    finally:
        # Logout from the API
        api.logout()
        logger.info("Logged out of the USGS API.")
