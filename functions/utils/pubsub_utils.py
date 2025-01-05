from google.cloud import pubsub_v1
import json
import os
import logging
import dotenv

logger = logging.getLogger(__name__)

PUBSUB_TOPIC = "download-tasks"
PUBSUB_EMULATOR_HOST = "localhost:8085"

dotenv.load_dotenv()


def publish_to_pubsub(dataset, entity_id, display_id):
    """Publish message to the Pub/Sub."""
    os.environ["PUBSUB_EMULATOR_HOST"] = PUBSUB_EMULATOR_HOST
    publisher = pubsub_v1.PublisherClient()
    topic_path = f"projects/{os.environ['GOOGLE_CLOUD_PROJECT']}/topics/{PUBSUB_TOPIC}"

    message = {
        "dataset": dataset,
        "entity_id": entity_id,
        "display_id": display_id
    }

    publisher.publish(topic_path, json.dumps(message).encode("utf-8"))
    logger.info(f"Published task for {display_id} to Pub/Sub.")
