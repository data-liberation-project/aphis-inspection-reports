# APHIS Report / License Scraper

*A collaboration between the [Data Liberation Project](https://www.data-liberation-project.org/) and [Big Local News](https://biglocalnews.org/content/about/).*

This repository aims to collect all of the following from the US Department of Agriculture's Animal and Plant Health Inspection Service [public search tools](https://efile.aphis.usda.gov/PublicSearchTool/s/):

- [Inspection reports](https://efile.aphis.usda.gov/PublicSearchTool/s/inspection-reports). (In progress.)
- All present and past licensees and registrants, from the same link above. (Not yet started.)
    - Note: Active licensees/registrants available in [APHIS spreadsheet](https://www.aphis.usda.gov/animal_welfare/downloads/List-of-Active-Licensees-and-Registrants.xlsx) linked from [public search landing page](https://efile.aphis.usda.gov/PublicSearchTool/s/).
- [Registrants' annual reports](https://efile.aphis.usda.gov/PublicSearchTool/s/annual-reports). (Not yet started)

## Inspection reports

### Main output

- [All fetched reports, searchable via DocumentCloud](https://www.documentcloud.org/app?q=%2Bproject%3Ausda-aphis-inspection-rep-211004%20)
- [All data fetched from web and parsed from PDFs](data/combined/inspections.csv)
    - [Just the metadata fetched from APHIS portal](data/fetched/inspections.csv)
    - [Just the data parsed from the PDFs](data/parsed/inspections.json)

### General observations

The data returned by the APHIS search portal contains the following variables:

Key|Description|Example
-----|-----|-----
`certNumber`|APHIS Certificate Number. A small proportion are blank.|93-R-0432
`customerNumber`|APHIS Customer Number. None are blank.|9191
`inspectionDate`|YYYY-MM-DD date of APHIS inspection. None are blank. Earliest collected here is 2014-01-30.|2022-11-14
`inspectionDateString`|MM/DD/YYYY date of APHIS inspection.|11/14/2022
`legalName`|Name of inspected licensee. Appears to be tied to the `customerNumber`. It *appears* that when APHIS updates this value, it is updated for all rows with the same `customerNumber`.|University of California-Berkeley
`siteName`|Name of inspected site. The same `certNumber` and `customerNumber` can relate to multiple sites. Unlike the `legalName`, it *appears* that APHIS does not change this retrospectively.|UNIVERSITY OF CALIFORNIA, BERKELEY
`reportLink`|URL of the inspection report PDF. Appears to be unique across rows, except for a handful (all pre-2019) with no link at all.|[https://aphis[...]](https://aphis--c.na21.content.force.com/sfc/dist/version/download/?oid=00Dt0000000GyZH&ids=068t000000gv9b5&d=%2Fa%2Ft0000001ZLeA%2FKg5uHjj9LGi0zJe1NX05AnSW950c7\_feljvRekhSHmU&asPdf=false)
`direct`|Number of "direct" noncompliant items.|0
`critical`|Number of "critical" noncompliant items.|0
`nonCritical`|Number of "non-critical" noncompliant items.|0
`teachableMoments`|Number of "teachable moment" noncompliant items.|0

### Fetching the inspection reports

#### Initial fetch

Although it should have been trivial for APHIS to provide a bulk download of the [inspection reports](https://efile.aphis.usda.gov/PublicSearchTool/s/inspection-reports), it does not. Moreover, although the public search tool runs on a publicly-inspectable API, both the tool and the API allows users to view no more than 2,100 results per query.

The script [`scripts/00-fetch-inspection-list.py`](scripts/00-fetch-inspection-list.py) solves these problems by iterating the `customerName` input fragment by fragment (e.g., `aa`, `ab`, `ac`) to assemble the full list, saving the results to [`data/fetched/inspections-by-letter.csv`](data/fetched/inspections-by-letter.csv). (Previous attempts including subdividing by state or certification type — with letter-by-letter searching a last resort — but APHIS's options for those search criteria appeared not to be comprehensive, based on the results.)

Those results are combined with all previously-identified inspections in [`data/fetched/inspections.csv`](data/fetched/inspections.csv), deduplicated, and resaved to [`data/fetched/inspections.csv`](data/fetched/inspections.csv).

This approach appears to capture all of the inspection reports, per a comparison of the number of results indicated in the public search tool and the number of rows in [`data/fetched/inspections-by-letter.csv`](data/fetched/inspections-by-letter.csv) at the time of the fetch.

Note: The results returned by the tool and API contain no unique inspection ID, so the results are deduplicated based on the full contents of each row.

#### Refreshing the data

The full fetch can take more than an hour, even when using a pool of four simultaneous processing pools. We can avoid refetching everything when refreshing the results by fetching the 2,100 most recent inspection reports (the query tool's default sorting order), which should suffice as long as it's run with some frequency. (As of late 2022, those 2,100 results go back to nearly four months prior.) This process is conducted via [`scripts/01-refresh-inspection-list.py`](scripts/01-refresh-inspection-list.py), which updates the file at [`data/fetched/inspections.csv`](data/fetched/inspections.csv).

__Note__: Because APHIS appears sometimes to update the `legalName` for a given `customerNumber`, and that this change appears to apply to all previous inspection data in the portal, running these data-refreshes may result in `data/fetched/inspections.csv` containing multiple variations of `legalName` for a given customer.

The script also updates [`data/fetched/inspections-search-total.txt`](data/fetched/inspections-search-total.txt) with the total number of results indicated in the [online search tool](https://efile.aphis.usda.gov/PublicSearchTool/s/inspection-reports).

Alternatively, to fully refetch the data, delete all files in the [`data/fetched/`](data/fetched/) directory and rerun [`scripts/00-fetch-inspection-list.py`](scripts/00-fetch-inspection-list.py).

### Downloading the inspection report PDFs

The script [`scripts/02-download-inspection-pdfs.py`](scripts/02-download-inspection-pdfs.py) downloads all inspection reports in [`data/fetched/inspections.csv`](data/fetched/inspections.csv) to [`pdfs/inspections/`](pdfs/inspections/). Because the data provided by the inspection search tool does not include the official inspection IDs, the filenames use the first 16 characters of the PDF URL's SHA1 hash hexdigest.

### Parsing the inspection report PDFs

The script [`scripts/03-parse-inspection-pdfs.py`](scripts/03-parse-inspection-pdfs.py) extracts data from each inspection report PDF and saves the results to [`data/parsed/`](data/parsed). Currently, only a minimal amount of information is being parsed, but further development should expand the details extracted in this step.

### Uploading the report PDFs to DocumentCloud

The script [`scripts/04-upload-inspection-pdfs.py`](scripts/04-upload-inspection-pdfs.py) uploads the PDFs to a [public project on DocumentCloud](https://www.documentcloud.org/app?q=%2Bproject%3Ausda-aphis-inspection-rep-211004%20), where they can be searched in bulk.

### Combining the results

The script [`scripts/05-combine-inspection-data.py`](scripts/05-combine-inspection-data.py) combines the results of the previous steps into a single CSV file, [`data/combined/inspections.csv`](data/combined/inspections.csv). In it, fields fetched from the web portal are prefixed with `web_`, those parsed from the PDFs with `pdf_`, and those relevant to DocumentCloud with `doccloud_`.

## Licensees

__TK - Not yet implemented.__

## Registrants

__TK - Not yet implemented.__

## Annual reports

__TK - Not yet implemented.__

## Running the code yourself

- Ensure you have Python 3 installed.
- From this repository, run `python -m venv venv` to create its virtual environment.
- Run `. venv/bin/activate && pip install -r requirements.txt` to install the necessary Python libraries.
- Consult the [`Makefile`](Makefile) to understand the available `make` commands.

## Questions

File an issue in this repository or email Jeremy Singer-Vine at `jsvine@gmail.com`.
