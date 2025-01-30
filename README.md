
# CloudImageManager

CloudImageManager automates the processing of satellite images using Google Cloud Functions, integrating with Google Earth Engine, Firestore, and Cloud Storage. The tool simplifies the workflow of fetching, processing, and saving image metadata, ensuring scalability and efficiency.
This backend enabling efficient and automated image management, getting information about network, stored data and cloud storage.
This is part of [cloud image manager app](https://cloudimagemanager.web.app).

## Features

- **Satellite Image Processing**: Fetch Landsat satellite images for specific regions.
- **Firestore Integration**: Save processed metadata directly to Firestore.
- **Cloud Storage Integration**: Upload processed images and metadata to Google Cloud Storage.
- **Configuration via `.env`**: Easy environment-based configuration.
- **Firebase Deployment**: Easily deploy functions using Firebase CLI.

## Requirements

- Python 3.7 or higher
- Firebase CLI installed (`npm install -g firebase-tools`)
- A Firebase project with:
  - Firestore and Cloud Storage enabled
  - Earth Engine APIs enabled
- Service account credentials for authentication
- Environment variables defined in a `.env` file

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Fluorky/CloudImageManager.git
   cd CloudImageManager/functions
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Initialize Firebase in your project directory:
   ```bash
   firebase init functions
   ```

4. Replace the `functions` directory with the one in this repository.

5. Create a `.env` file in the `functions` directory with the following structure:
   ```env
   USGS_API_KEY = usgs_api_key
   COLLECTION_NAME_DEFAULT=your_landsat_collection_name
   BUCKET_NAME=your_cloud_storage_bucket
   CONFIG_PATH=path_to_config_in_bucket.json
   PROJECT_ID=your_cloud_project_name
   FIRESTORE_EMULATOR_HOST=localhost:8080  # Optional: For local debugging
   STORAGE_EMULATOR_HOST=http://localhost:9090  # Optional: For local debugging
   ```

## Deployment

1. Login to Firebase:
   ```bash
   firebase login
   ```

2. Deploy the function:
   ```bash
   firebase deploy --only functions
   ```

3. Deployment:
   ```bash
   firebase deploy
   ```

## Usage

### Environment Configuration
Ensure your `.env` file is properly set up:
- **BUCKET_NAME**: Name of the Cloud Storage bucket where images and metadata will be stored.
- **CONFIG_PATH**: Path to the configuration file in the bucket, defining the region and radius.

### Testing Locally
To test the function locally, set the `FIRESTORE_EMULATOR_HOST` and `STORAGE_EMULATOR_HOST` environment variables to use Firebase and Cloud Storage emulators.

Start the emulator locally:
```bash
firebase emulators:start
```

### Making API Requests
The function can be triggered via an HTTP request. Example request body:
```json
{
  "collection": "LANDSAT/LC09/C02/T2_TOA"
}
```

Send a POST request to the deployed functions:
```bash
curl -X POST https://REGION-PROJECT_ID.cloudfunctions.net/landsat_cron     -H "Content-Type: application/json"     -d '{"collection": "LANDSAT/LC09/C02/T2_TOA"}'
```

### Workflow
1. The function fetches region data from `CONFIG_PATH` in Cloud Storage.
2. Images from the specified Landsat collection are processed.
3. Metadata is saved in Firestore, and images are uploaded to Cloud Storage.
4. Logs and errors are recorded in Firestore for monitoring.

## Example Configuration File
The `CONFIG_PATH` file in your bucket should look like this:
```json
{
  "coordinates": [6.746, 46.529],
  "radius": 10000
}
```

## Contributing
Contributions are welcome! Fork this repository and submit a pull request.

## License
This project is licensed under the MIT License.
