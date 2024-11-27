from eodag import EODataAccessGateway
from eodag.utils.logging import setup_logging
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Fetch credentials from .env
USGS_USERNAME = os.getenv("USGS_USERNAME")
USGS_PASSWORD = os.getenv("USGS_PASSWORD")

# Initialize EODataAccessGateway
setup_logging(0)
dag = EODataAccessGateway()

# Configure credentials dynamically
dag.set_preferred_provider("usgs")  # Ensure USGS is the preferred provider
dag.update_providers_config(
    usgs={"credentials": {"username": USGS_USERNAME, "password": USGS_PASSWORD}}
)

# Define search parameters
product_type = "LANDSAT_C2L2"  # Landsat Collection 2 Level 2 products
geom = {
    "lonmin": -5.0,  # Minimum longitude
    "latmin": 40.0,  # Minimum latitude
    "lonmax": 5.0,   # Maximum longitude
    "latmax": 50.0   # Maximum latitude
}
start, end = "2020-01-01", "2020-12-31"  # Time range

# Search for products
search_results, total_count = dag.search(
    productType=product_type,
    geom=geom,
    start=start,
    end=end
)

print(f"Found {total_count} products")

# Download the first product found
if search_results:
    product = search_results[0]
    dag.download(product)
else:
    print("No products found for the specified criteria.")
