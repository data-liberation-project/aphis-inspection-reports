# APHIS Inspection Report Scraper

*A collaboration between the [Data Liberation Project](https://www.data-liberation-project.org/) and [Big Local News](https://biglocalnews.org/content/about/).*

This repository aims to collect, and extract data from, all [publicly-available inspection reports](https://efile.aphis.usda.gov/PublicSearchTool/s/inspection-reports) published by the US Department of Agriculture's [Animal and Plant Health Inspection Service](https://www.aphis.usda.gov/aphis/home/) (APHIS).

## Overview

### What are these inspections?

[As APHIS explains](https://www.aphis.usda.gov/aphis/ourfocus/animalwelfare/sa_awa/awa-inspection-and-annual-reports):

> USDA Animal Care inspectors conduct routine, unannounced inspections of all entities licensed/registered under the Animal Welfare Act. Inspectors conduct three types of inspections: 1) pre-licensing inspections, to make sure the applicant can meet the federal standards prior to being licensed/registered; 2) routine, unannounced compliance inspections of all entities to make sure they are adhering to the federal standards and regulations; and 3) focused inspections based upon public complaints or allegations of unlicensed activities. During routine inspections, USDA reviews the premises, records, husbandry practices, program of veterinary care and animal handling procedures to ensure the animals are receiving humane care. The frequency of inspections is based on several factors – including an entity’s compliance history. USDA inspects research facilities that use regulated animals at least once a year.

### What data have you collected?

For every inspection we've been able to identify through the [APHIS inspections portal](https://efile.aphis.usda.gov/PublicSearchTool/s/inspection-reports), we've collected:

- __Inspection metadata__ from the portal, such as the inspection date, licensee, and violation counts.
- The __inspection report PDF__ linked from the portal.
- Additional __data parsed from the PDF__, such as the type of inspection and the list of inspected species

The file [METHODOLOGY.md](METHODOLOGY.md) describes the process of scraping, parsing, uploading, and merging the inspection reports.


### What data are you providing?

All of the data collected and processed are available in this repository, some more raw/processed than others. We've also combined these records into the following __main resources__:

- The data from all inspections, available as [one core CSV spreadsheet](data/combined/inspections.csv) plus [another sheet listing species-level counts of animals inspected, per inspection](data/combined/inspections-species.csv). See "Data Dictionary" below for details.
- All inspection report PDFs, available [directly](pdfs/inspections/) and as [a searchable project on DocumentCloud](https://www.documentcloud.org/app?q=%2Bproject%3Ausda-aphis-inspection-rep-211004%20)
- An [RSS feed](data/combined/latest-inspections.rss) listing the inspections we've most recently *discovered*


## Data Dictionary

### Core inspection data

The file [`data/combined/inspections.csv`](data/combined/inspections.csv) represents each inspection report collected by the code in this repository. Its column names use four prefixes, to clarify the source of each data-point:

- `web_`: Data fetched from the web portal
- `pdf_`: Data extracted from the PDFs
- `doccloud_`: Data relevant to the uploading of PDFs to [DocumentCloud](https://www.documentcloud.org/app?q=%2Bproject%3Ausda-aphis-inspection-rep-211004%20)
- `[no prefix]`: Data in columns without any of these prefixes, such as `licenseType`, have been derived from one or more of the prefixed columns.


Column|Description|Example
------|-----------|-------
`web_certNumber`|APHIS Certificate Number. A small proportion are blank.|93-R-0432
`web_customerNumber`|APHIS Customer Number. None are blank.|9191
`web_inspectionDate`|YYYY-MM-DD date of APHIS inspection. None are blank. Earliest collected here is 2014-01-30.|2022-11-14
`web_legalName`|Name of inspected licensee. Appears to be tied to the `customerNumber`. It *appears* that when APHIS updates this value, it is updated for all rows with the same `customerNumber`.|University of California-Berkeley
`web_siteName`|Name of inspected site. The same `certNumber` and `customerNumber` can relate to multiple sites. It appears that APHIS sometimes changes this value retrospectively.|UNIVERSITY OF CALIFORNIA, BERKELEY
`web_reportLink`|URL of the inspection report PDF. Appears to be unique across rows, except for a handful (all pre-2019) with no link at all.|[https://aphis[...]](https://aphis--c.na21.content.force.com/sfc/dist/version/download/?oid=00Dt0000000GyZH&ids=068t000000gv9b5&d=%2Fa%2Ft0000001ZLeA%2FKg5uHjj9LGi0zJe1NX05AnSW950c7\_feljvRekhSHmU&asPdf=false)
`web_direct`|Number of "direct" noncompliant items.|0
`web_critical`|Number of "critical" noncompliant items.|0
`web_nonCritical`|Number of "non-critical" noncompliant items.|0
`web_teachableMoments`|Number of "teachable moment" noncompliant items.|0
`hash_id`|The first 16 characters of the SHA1 hash hexdigest of the PDF URL (`web_reportLink`) `ids={...}` parameter. This ID acts as the unique identifier for each PDF in the portal, and follows the PDF throughout the rest of the data processing.|4e616aea5de92ead
`discovered`|A UTC timestamp indicating when *our pipeline* first noticed the report. Due to vagaries in the scraping process, this does not necessarily indicate when *APHIS* published the report. Reports identified before our timestamping feature was added are given a placeholder timestamp of `1970-01-01 00:00:00+00:00`.|2023-02-07 18:13:44+00:00
`pdf_insp_id`|The identifier printed at the top-right of the inspection inspection report. | INS-0000826614                                                                   |
`pdf_layout`|There appear to be two types of report layouts, possibly generated by different versions of software. This column's values are arbitrarily named, with `a` corresponding to one layout and `b` to the other. | b 
`pdf_customer_id`|The "Customer ID" printed in the report heading; should match the `web_customerNumber`.| 9191 
`pdf_customer_name`|The name printed in top-left of the report heading.| University of California-Berkeley 
`pdf_customer_addr`|The address printed in the top-left of the report heading.| 119 California Hall Berkeley, CA 94720 
`pdf_certificate`|The "Certificate" printed in the report heading; should match `web_certNumber`| 93-R-0432 
`pdf_site_id`|The "Site" identifier printed in the report heading. | 001 
`pdf_site_name`|The text directly below the "Site" identifier printed in the report heading.| UNIVERSITY OF CALIFORNIA, BERKELEY 
`pdf_insp_type`|The "Type" printed in the report heading.| ROUTINE INSPECTION 
`pdf_date`|The "Date" printed in the report heading; should match `web_inspectionDate`, but instead in the `DD-MONTHABBR-YYYY` format.| 14-NOV-2022 
`pdf_animals_total`|The "Total" value printed at the end of the report's "Species Inspected" section.| 697 
`doccloud_url`|The DocumentCloud URL to which this repository has uploaded the PDF. | [https://www.documentcloud.org/[...]](https://www.documentcloud.org/documents/23582024-aphis-inspection-ins-0000826614)
`licenseType`|The type of license, extracted from `web_certNumber`. | R 

### Inspected species data

The file [`data/combined/inspections-species.csv`](data/combined/inspections-species.csv) contains all "Species Inspected" tables at the end of each report PDF, linkable back to the main file via `hash_id`.


Column|Description|Example
------|-----------|-------
`hash_id`|The `hash_id` of the inspection report PDF|4e616aea5de92ead
`count`|The value in the PDF table's "Count" column.|53
`scientific`|The value in the PDF table's "Scientific Name" column.|Capra hircus
`common`|The value in the PDF table's "Common Name" column.|DOMESTIC GOAT


## Caveats and Limitations

- Inspections are not immediately available through the APHIS portal. Most appear to be posted roughly four weeks after the inspection date, but others are not posted until much later.
- The APHIS portal [appears to link a (small) number of inspection entries to the wrong PDFs](https://github.com/data-liberation-project/aphis-inspection-reports/issues/23).

## Additional resources

- The USDA's 350-page [Animal Welfare Inspection Guide](https://www.aphis.usda.gov/animal_welfare/downloads/Animal-Care-Inspection-Guide.pdf) provides helpful context and details regarding the inspection process and outcomes.
- APHIS provides a [spreadsheet of active licensees and registrants](https://www.aphis.usda.gov/animal_welfare/downloads/List-of-Active-Licensees-and-Registrants.xlsx), linked from its [public search landing page](https://efile.aphis.usda.gov/PublicSearchTool/s/).

## Running the code yourself

- Ensure you have Python 3 installed
- From this repository, run `python3 -m venv venv` to create its virtual environment
- Run `. venv/bin/activate` to activate the virtual environment
- Run `pip install -r requirements.txt` to install the necessary Python libraries
- Consult the [`Makefile`](Makefile) to understand the available `make` commands

## Licensing

This repository's code is available under the [MIT License terms](https://opensource.org/license/mit/). The raw data files (in `data/fetched`) and PDFs are public domain. All other data files are available under Creative Commons' [CC BY-SA 4.0 license terms](https://creativecommons.org/licenses/by-sa/4.0/).

## Questions?

File an issue in this repository or email Jeremy Singer-Vine at `jsvine@gmail.com`.
