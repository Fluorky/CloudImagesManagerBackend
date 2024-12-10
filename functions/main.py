import os
import tarfile
import json
import logging
from multiprocessing import Process, Queue
from usgsxplore.api import API
from firebase_functions import https_fn
from firebase_admin import initialize_app
import dotenv
import time

# Initialize Firebase Admin
initialize_app()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
dotenv.load_dotenv()

USGS_USERNAME = os.environ.get("USGS_USERNAME")
USGS_PASSWORD = os.environ.get("USGS_PASSWORD")

# Set up directories
base_dir = os.getcwd()
downloads_dir = os.path.join(base_dir, "downloads")
extracted_dir = os.path.join(base_dir, "extracted")
metadata_dir = os.path.join(base_dir, "metadata")

os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(extracted_dir, exist_ok=True)
os.makedirs(metadata_dir, exist_ok=True)


def extract_tar_file(input_tar_file_path, extract_to, metadata_base):
    """
    Extracts a tar file to the specified directory and saves metadata for each file.
    """
    try:
        if tarfile.is_tarfile(input_tar_file_path):
            with tarfile.open(input_tar_file_path, "r") as tar:
                for member in tar.getmembers():
                    tar.extract(member, extract_to)
                    file_path = os.path.join(extract_to, member.name)
                    file_metadata = {
                        "name": member.name,
                        "size": member.size,
                        "type": "directory" if member.isdir() else "file",
                        "modified_time": member.mtime,
                        "path": file_path,
                    }

                    metadata_file_path = os.path.join(metadata_base, f"{member.name}.json")
                    os.makedirs(os.path.dirname(metadata_file_path), exist_ok=True)
                    with open(metadata_file_path, "w") as meta_file:
                        json.dump(file_metadata, meta_file, indent=4)
                    logger.info(f"Saved metadata for {member.name} to {metadata_file_path}")
        else:
            logger.warning(f"File is not a valid tar archive: {input_tar_file_path}")
    except Exception as err:
        logger.error(f"Failed to extract {input_tar_file_path}: {err}")


def download_worker(dataset, entity_id, display_id, output_dir, queue):
    """
    Downloads a single file and puts the result in the queue.
    """
    try:
        api = API(username=USGS_USERNAME, password=USGS_PASSWORD)
        api.download(dataset=dataset, entity_ids=[entity_id], output_dir=output_dir)
        queue.put({"status": "success", "entity_id": entity_id, "display_id": display_id})
    except Exception as e:
        queue.put({"status": "error", "entity_id": entity_id, "display_id": display_id, "error": str(e)})


@https_fn.on_request()
def search_and_download(req: https_fn.Request) -> https_fn.Response:
    """
    Firebase HTTP function to search Landsat data, download results, extract files, and save metadata.
    """
    try:
        data = req.get_json()
        if not data:
            return https_fn.Response("Invalid request: JSON body is required", status=400)

        dataset = data.get("dataset", "landsat_etm_c2_l2")
        bounding_box = data.get("bounding_box", [21.0, 52.0, 22.0, 53.0])
        date_interval = data.get("date_interval", ["2023-01-01", "2023-06-10"])
        max_results = data.get("max_results", 4)

        logger.info("Starting Landsat data search...")
        api = API(username=USGS_USERNAME, password=USGS_PASSWORD)

        search_results = api.search(
            dataset=dataset,
            bbox=bounding_box,
            date_interval=date_interval,
            max_results=max_results,
        )

        if not search_results:
            logger.info("No results found for the given search criteria.")
            return https_fn.Response(
                {"status": "success", "message": "No search results found"}, status=200
            )

        logger.info(f"Found {len(search_results)} products.")

        results = []
        processes = []
        queue = Queue()

        for item in search_results:
            entity_id = item["entityId"]
            display_id = item["displayId"]
            logger.info(f"Preparing to download file: {display_id} (ID: {entity_id})")

            process = Process(target=download_worker, args=(dataset, entity_id, display_id, downloads_dir, queue))
            process.start()
            processes.append(process)

        # Wait for all processes to finish
        for process in processes:
            process.join()

        # Process download results
        while not queue.empty():
            result = queue.get()
            if result["status"] == "error":
                logger.error(f"Failed to download {result['display_id']}: {result['error']}")
                continue

            logger.info(f"Downloaded file for ID: {result['entity_id']}")
            tar_file_path = os.path.join(downloads_dir, f"{result['display_id']}.tar")
            extract_path = os.path.join(extracted_dir, result["display_id"])
            file_metadata_dir = os.path.join(metadata_dir, result["display_id"])

            if os.path.isfile(tar_file_path):
                os.makedirs(extract_path, exist_ok=True)
                os.makedirs(file_metadata_dir, exist_ok=True)
                extract_tar_file(tar_file_path, extract_path, file_metadata_dir)

                results.append({
                    "entity_id": result["entity_id"],
                    "display_id": result["display_id"],
                    "download_path": tar_file_path,
                    "extract_path": extract_path,
                    "metadata_path": file_metadata_dir,
                })
            else:
                logger.warning(f"File {tar_file_path} not found or is not a tar file.")

        return https_fn.Response({"status": "success", "results": results}, status=200)

    except Exception as e:
        logger.error(f"Error during processing: {e}")
        return https_fn.Response({"status": "error", "message": str(e)}, status=500)
