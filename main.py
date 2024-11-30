import logging
from eodag import EODataAccessGateway
from eodag.utils.logging import setup_logging

# Configure logging
setup_logging(0)
logger = logging.getLogger("eodag")
logger.setLevel(logging.DEBUG)

# Initialize EODataAccessGateway
dag = EODataAccessGateway("config.yaml")

# Set the preferred provider
preferred_provider = "usgs"  # Or 'planetary_computer' if necessary
dag.set_preferred_provider(preferred_provider)

# Define search parameters
product_type = "LANDSAT_C2L2"
geom = {
    "lonmin": 21.0,  # Minimum longitude
    "latmin": 52.0,  # Minimum latitude
    "lonmax": 22.0,  # Maximum longitude
    "latmax": 53.0   # Maximum latitude
}
start, end = "2023-01-01", "2023-01-10"  # Date range

# Search for products
logger.info(f"Searching for Landsat products using provider '{preferred_provider}'...")
search_results = dag.search(
    productType=product_type,
    geom=geom,
    start=start,
    end=end
)
logger.info(f"Search result: {search_results}")
if search_results:
    for i in range(len(search_results)):
        product = search_results[i]
        product_path = product.download()
        logger.info(product_path)
#
else:
    logger.error("No products found for the specified criteria.")


# else:
#     for product in search_results:
#         try:
#             # Use the remote location for manual download
#             remote_url = product.remote_location
#             print(f"Downloading product from: {remote_url}")
#
#             response = requests.get(remote_url, stream=True)
#             if response.status_code == 200:
#                 filename = f"{product.properties['id']}.json"
#                 with open(filename, "wb") as f:
#                     for chunk in response.iter_content(chunk_size=8192):
#                         f.write(chunk)
#                 print(f"Downloaded {filename}")
#             else:
#                 print(f"Failed to download {product.properties['id']}: HTTP {response.status_code}")
#         except Exception as e:
#             print(f"Error while downloading {product.properties['id']}: {e}")
