import os
import ee
import requests
from flask import Flask, jsonify
from google.cloud import storage

# Initialize Flask application
app = Flask(__name__)

# Initialize Google Earth Engine
ee.Initialize()

# Configure Google Cloud Storage to work with Firebase emulator
os.environ["STORAGE_EMULATOR_HOST"] = "http://127.0.0.1:9199"
bucket_name = "cloudimagemanager.appspot.com"  # Use the bucket name from the emulator

# Initialize GCS client
storage_client = storage.Client()
bucket = storage_client.bucket(bucket_name)


@app.route('/landsat', methods=['GET'])
def get_landsat_image():
    try:
        # Retrieve Landsat data
        collection = ee.ImageCollection('LANDSAT/LC09/C02/T2_TOA') \
            .filterDate('2022-01-01', '2022-02-01') \
            .select(['B4', 'B3', 'B2'])

        image = collection.median()

        vis_params = {
            'min': 0.0,
            'max': 0.4,
            'bands': ['B4', 'B3', 'B2']
        }

        # Define geographic region
        region = ee.Geometry.Point([6.746, 46.529]).buffer(10000).bounds()

        # Generate thumbnail URL for the image
        url = image.getThumbURL({
            'region': region,
            'dimensions': 512,
            'format': 'png',
            **vis_params
        })

        # Download the image from the URL
        response = requests.get(url)
        response.raise_for_status()

        # Save the image to Firebase Storage emulator
        blob = bucket.blob('landsat_image.png')
        blob.upload_from_string(response.content, content_type='image/png')

        return jsonify({"message": "Image saved successfully in emulator!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(host='127.0.0.1', port=8082)

# from usgs_downloader import search_and_download
#
#
# def main():
#     """
#     Main function to execute the script.
#     """
#     # Parameters
#     dataset = "landsat_etm_c2_l2"  # Example dataset
#     bounding_box = (21.0, 52.0, 22.0, 53.0)  # (xmin, ymin, xmax, ymax)
#     date_interval = ("2023-01-01", "2023-06-10")  # (start_date, end_date)
#     max_results = 4
#
#     # Run the search and download process
#     search_and_download(dataset, bounding_box, date_interval, max_results)
#
#
# if __name__ == "__main__":
#     main()
