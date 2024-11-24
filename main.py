import os
from eodag import EODataAccessGateway, setup_logging
from datetime import datetime

setup_logging(0)

config_file = "config.yaml"
dag = EODataAccessGateway(config_file)

search_results, total_count = dag.search(
    # productType='S2_MSI_L1C',
    productType='LANDSAT_C2L2',
    geom={'lonmin': 1, 'latmin': 50, 'lonmax': 2, 'latmax': 54},
    start='2024-11-01',
    end='2024-11-04',
    # provider='usgs'
)
search_results

for i in range(len(search_results)):
    product = search_results[i]
    product_path = product.download()
    print(product_path)
