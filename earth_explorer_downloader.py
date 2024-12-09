import os
from dotenv import load_dotenv
from landsatxplore.api import API
from landsatxplore.earthexplorer import EarthExplorer

# Load environment variables from .env file
load_dotenv()

# Load sensitive data from environment variables
username = os.environ.get('USGS_USERNAME')  # Set your EarthExplorer username in environment variables
password = os.environ.get('USGS_PASSWORD')  # Set your EarthExplorer password in environment variables
output_dir = os.environ.get('OUTPUT_DIR')


# Check if credentials are set
if not username or not password:
    raise EnvironmentError("Missing EarthExplorer credentials. Set EARTHEXPLORER_USERNAME and EARTHEXPLORER_PASSWORD "
                           "in environment variables.")

# Search parameters
dataset = 'landsat_ot_c2_l1'  # Landsat 8 Collection 2 Level 1
latitude = 52.2297700  # Latitude of Warsaw
longitude = 21.0117800  # Longitude of Warsaw
start_date = '2023-1-21'  # Start date
end_date = '2023-11-21'  # End date
max_cloud_cover = 10  # Maximum cloud cover in percentage

# Initialize API
api = API(username, password)
# Search for scenes
scenes = api.search(
    dataset=dataset,
    latitude=latitude,
    longitude=longitude,
    start_date=start_date,
    end_date=end_date,
    max_cloud_cover=max_cloud_cover
)

print(f'Found {len(scenes)} scenes.')

# Download scenes
ee = EarthExplorer(username, password)

for scene in scenes:
    scene_id = scene['landsat_product_id']
    print(f'Downloading scene {scene_id}...')
    ee.download(scene_id, output_dir=output_dir)

# End session
ee.logout()
api.logout()


