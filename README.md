
# CloudImageManager

CloudImageManager automates the processing of satellite images using Google Cloud Functions, integrating with Google Earth Engine, Firestore, and Cloud Storage. The tool simplifies the workflow of fetching, processing, and saving image metadata, ensuring scalability and efficiency.
This backend enabling efficient and automated image management, getting information about network, stored data and cloud storage.
This is part of [cloud image manager app](https://cloudimagemanager.web.app).

## Features

- **Satellite Image Processing**: Fetch Landsat satellite images for specific regions and process them efficiently.
- **Automated Image Scaling**: Resize images to HD resolution (720p) for optimized storage and access.
- **Firestore Integration**: Save processed metadata directly to Firestore for real-time database management.
- **Cloud Storage Integration**: Upload and manage processed images and metadata in Google Cloud Storage.
- **Network Traffic Monitoring**: Retrieve and analyze network traffic data for storage usage insights.
- **Firebase Statistics**: Fetch and analyze Firebase performance metrics.
- **Configuration via `.env`**: Easy environment-based configuration for custom deployments.
- **Firebase Deployment**: Easily deploy functions using Firebase CLI with a single command.
- **Local Testing Support**: Run and debug functions locally using Firebase emulators.

## Requirements

- Python 3.7 or higher
- Firebase CLI installed (`npm install -g firebase-tools`)
- A Firebase project with:
  - Firestore and Cloud Storage enabled
  - Earth Engine APIs enabled
- Service account credentials for authentication
- Environment variables defined in a `.env` file

## Project Structure
```
CloudImagesManagerBackend/
│── functions/              # Contains Firebase functions (backend logic)
│   ├── main.py             # Main function entry point
│   ├── config.py           # Configuration settings
│   ├── firebase_stats.py   # Firebase statistics handling
│   ├── images_blob_information.py # Image processing module
│   ├── landsat_cron.py     # Landsat image automation
│   ├── network_information.py # Network information module
│   ├── scaled_image.py     # Image scaling utility
│   ├── utils.py            # Helper functions
│   ├── requirements.txt    # Dependencies for Python
│── firestore.rules         # Firestore security rules
│── storage.rules           # Cloud Storage security rules
│── firebase.json           # Firebase configuration file
│── .firebaserc             # Firebase project settings
│── README.md               # Project documentation
```

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

### Available Functions

#### 1. Fetch Firebase Statistics
**Function:** `get_firebase_stats`
```bash
curl -X GET https://REGION-PROJECT_ID.cloudfunctions.net/get_firebase_stats
```

#### 2. Get Total Image Size from Cloud Storage
**Function:** `get_total_image_size`
```bash
curl -X GET "https://REGION-PROJECT_ID.cloudfunctions.net/get_total_image_size?folder=landsat_images/"
```

#### 3. Fetch Landsat Satellite Images
**Function:** `landsat_cron`
```bash
curl -X POST https://REGION-PROJECT_ID.cloudfunctions.net/landsat_cron \
     -H "Content-Type: application/json" \
     -d '{"collection": "LANDSAT/LC09/C02/T2_TOA"}'
```

#### 4. Fetch Network Traffic Data
**Function:** `get_network_traffic`
```bash
curl -X POST https://REGION-PROJECT_ID.cloudfunctions.net/get_network_traffic \
     -H "Content-Type: application/json" \
     -d '{"start_date": "2024-01-01", "end_date": "2024-02-01"}'
```

#### 5. Scale Images to HD Resolution (720p)
**Function:** `get_scaled_images`
```bash
curl -X GET https://REGION-PROJECT_ID.cloudfunctions.net/get_scaled_images
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
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m "Add new feature"`).
4. Push to the branch (`git push origin feature-name`).
5. Create a Pull Request.

## License
This project is licensed under the MIT License.
