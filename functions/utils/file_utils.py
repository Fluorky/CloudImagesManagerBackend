import tarfile
import os
import json
import logging

logger = logging.getLogger(__name__)


def extract_tar_file(input_tar_file_path, extract_to, metadata_base):
    """Unpacking TAR file and save metadata."""
    try:
        if tarfile.is_tarfile(input_tar_file_path):
            with tarfile.open(input_tar_file_path, "r") as tar:
                tar.extractall(path=extract_to)
                logger.info(f"Extracted {input_tar_file_path} to {extract_to}")

                for member in tar.getmembers():
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
