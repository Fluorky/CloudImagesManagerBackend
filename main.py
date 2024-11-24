from eodag import EODataAccessGateway
from eodag.utils.logging import setup_logging
import os

# Set up logging
setup_logging(0)

# Initialize EODataAccessGateway
dag = EODataAccessGateway()

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
