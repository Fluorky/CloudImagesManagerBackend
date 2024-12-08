import logging
from eodag import EODataAccessGateway

logger = logging.getLogger("eodag")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()  # Create a stream handler for console output
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')  # Set the log format
console_handler.setFormatter(formatter)  # Attach the formatter to the handler
logger.addHandler(console_handler)  # Add the handler to the logger
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
        # print(product_path)
else:
    logger.error("No products found for the specified criteria.")
