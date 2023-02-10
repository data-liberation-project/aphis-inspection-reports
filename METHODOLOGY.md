# Methodology

This document describes the process for scraping, parsing, uploading, and merging the inspection reports.

## Fetching the inspection reports

### Initial fetch

Although it should have been trivial for APHIS to provide a bulk download of the [inspection reports](https://efile.aphis.usda.gov/PublicSearchTool/s/inspection-reports), it does not. Moreover, although the public search tool runs on a publicly-inspectable API, both the tool and the API allows users to view no more than 2,100 results per query.

The script [`scripts/00-fetch-inspection-list.py`](scripts/00-fetch-inspection-list.py) solves these problems by iterating the `customerName` input fragment by fragment (e.g., `aa`, `ab`, `ac`) to assemble the full list, saving the results to [`data/fetched/inspections-by-letter.csv`](data/fetched/inspections-by-letter.csv). (Previous attempts including subdividing by state or certification type — with letter-by-letter searching a last resort — but APHIS's options for those search criteria appeared not to be comprehensive, based on the results.)

Those results are combined with all previously-identified inspections in [`data/fetched/inspections.csv`](data/fetched/inspections.csv), deduplicated, and resaved to [`data/fetched/inspections.csv`](data/fetched/inspections.csv).

This approach appears to capture all of the inspection reports, per a comparison of the number of results indicated in the public search tool and the number of rows in [`data/fetched/inspections-by-letter.csv`](data/fetched/inspections-by-letter.csv) at the time of the fetch.

Note: The results returned by the tool and API contain no unique inspection ID, so the results are deduplicated based on the full contents of each row.

### Refreshing the data

The full fetch can take more than an hour, even when using a pool of four simultaneous processing pools. We can avoid refetching everything when refreshing the results by fetching the 2,100 most recent inspection reports (the query tool's default sorting order), which should suffice as long as it's run with some frequency. (As of late 2022, those 2,100 results go back to nearly four months prior.) This process is conducted via [`scripts/01-refresh-inspection-list.py`](scripts/01-refresh-inspection-list.py), which updates the file at [`data/fetched/inspections.csv`](data/fetched/inspections.csv).

__Note__: Because APHIS appears sometimes to update the `legalName` for a given `customerNumber`, and that this change appears to apply to all previous inspection data in the portal, running these data-refreshes may result in `data/fetched/inspections.csv` containing multiple variations of `legalName` for a given customer.

The script also updates [`data/fetched/inspections-search-total.txt`](data/fetched/inspections-search-total.txt) with the total number of results indicated in the [online search tool](https://efile.aphis.usda.gov/PublicSearchTool/s/inspection-reports).

Alternatively, to fully refetch the data, delete all files in the [`data/fetched/`](data/fetched/) directory and rerun [`scripts/00-fetch-inspection-list.py`](scripts/00-fetch-inspection-list.py).

## Downloading the inspection report PDFs

The script [`scripts/02-download-inspection-pdfs.py`](scripts/02-download-inspection-pdfs.py) downloads all inspection reports in [`data/fetched/inspections.csv`](data/fetched/inspections.csv) to [`pdfs/inspections/`](pdfs/inspections/). Because the data provided by the inspection search tool does not include the official inspection IDs, the filenames use the `hash_id` value (the first 16 characters of the SHA1 hash hexdigest of the PDF URL's `ids={...}` parameter).

described above.

## Parsing the inspection report PDFs

The script [`scripts/03-parse-inspection-pdfs.py`](scripts/03-parse-inspection-pdfs.py) extracts data from each inspection report PDF and saves the results to [`data/parsed/`](data/parsed). Most of the core data points are extracted. Notable exceptions include the date the report was completed (rather than published), and the full text of the inspections.

## Uploading the report PDFs to DocumentCloud

The script [`scripts/04-upload-inspection-pdfs.py`](scripts/04-upload-inspection-pdfs.py) uploads the PDFs to a [public project on DocumentCloud](https://www.documentcloud.org/app?q=%2Bproject%3Ausda-aphis-inspection-rep-211004%20), where they can be searched in bulk.

## Combining the results

The script [`scripts/05-combine-inspection-data.py`](scripts/05-combine-inspection-data.py) combines the results of the previous steps into two CSV files, [`data/combined/inspections.csv`](data/combined/inspections.csv) and [`data/combined/inspections-species.csv`](data/combined/inspections-species.csv).

The script [`scripts/06-update-rss.py`](scripts/06-update-rss.py) generates [`data/combined/latest-inspections.rss`](data/combined/latest-inspections.rss), an RSS file listing the most recently-discovered inspections.
