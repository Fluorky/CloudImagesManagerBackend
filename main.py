from usgs_downloader import search_and_download


def main():
    """
    Main function to execute the script.
    """
    # Parameters
    dataset = "landsat_etm_c2_l2"  # Example dataset
    bounding_box = (21.0, 52.0, 22.0, 53.0)  # (xmin, ymin, xmax, ymax)
    date_interval = ("2023-01-01", "2023-06-10")  # (start_date, end_date)
    max_results = 4

    # Run the search and download process
    search_and_download(dataset, bounding_box, date_interval, max_results)


if __name__ == "__main__":
    main()
