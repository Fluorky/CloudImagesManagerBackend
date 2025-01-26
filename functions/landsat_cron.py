import ee
import requests
import json
from datetime import datetime, timedelta
from firebase_functions import https_fn
from config import firestore_client, bucket, BUCKET_NAME, CONFIG_PATH
from utils import get_region_from_cloud_storage, flatten_data, log_error_to_firestore


@https_fn.on_request()
def landsat_cron(req: https_fn.Request) -> https_fn.Response:
    try:
        collection_name = req.get_json().get("collection", "LANDSAT/LC09/C02/T2_TOA")

        today = datetime.utcnow()
        two_years = timedelta(days=730)
        quarter = timedelta(days=90)
        end_date = (today - two_years).date().isoformat()
        start_date = (today - two_years - quarter).date().isoformat()

        region_coordinates, region_radius = get_region_from_cloud_storage(bucket, CONFIG_PATH)
        region = ee.Geometry.Point(region_coordinates).buffer(region_radius).bounds()
        collection = (
            ee.ImageCollection(collection_name)
            .filterDate(start_date, end_date)
            .filterBounds(region)
            .select(["B4", "B3", "B2"])
        )

        image_count = collection.size().getInfo()
        if image_count == 0:
            log_error_to_firestore(firestore_client, "No images found")
            return https_fn.Response(json.dumps({"message": "No images found"}), status=404)

        saved_images = []
        saved_metadata = []

        # Create empty collection `landsat_metadata_changed` in Firestore if it does not exist
        if not firestore_client.collection("landsat_metadata_changed").document("placeholder").get().exists:
            firestore_client.collection("landsat_metadata_changed").document("placeholder").set({})

        images = collection.toList(image_count)
        for i in range(image_count):
            image = ee.Image(images.get(i))
            raw_metadata = image.getInfo()
            image_id = raw_metadata.get("id").split("/")[-1]

            properties = flatten_data(raw_metadata.get("properties", {}))
            metadata = {
                "type": "Image",
                "id": image_id,
                "location": {"coordinates": region_coordinates, "region_radius": region_radius},
                "properties": properties,
            }

            firestore_client.collection("landsat_metadata").document(image_id).set(metadata)
            saved_metadata.append(image_id)

            vis_params = {"min": 0.0, "max": 0.4, "bands": ["B4", "B3", "B2"]}
            url = image.getThumbURL({"region": region, "dimensions": 512, "format": "png", **vis_params})
            response = requests.get(url)
            response.raise_for_status()

            image_blob_name = f"landsat_images/{image_id}.png"
            bucket.blob(image_blob_name).upload_from_string(response.content, content_type="image/png")
            saved_images.append(image_blob_name)

        return https_fn.Response(
            json.dumps({"message": "Cron job executed successfully", "image_count": image_count, "saved_images": saved_images}),
            status=200,
        )
    except Exception as e:
        log_error_to_firestore(firestore_client, str(e))
        return https_fn.Response(json.dumps({"error": str(e)}), status=500)
