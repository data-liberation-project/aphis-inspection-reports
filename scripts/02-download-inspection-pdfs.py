"""Download inspection PDFs."""
import csv
import sys
from pathlib import Path

import requests
from lib.aphis import hash_id_from_url
from retry import retry


@retry(tries=10, delay=30)
def fetch(link: str, timeout: int = 60):
    """Request the provided URL and return the content."""
    res = requests.get(link, timeout=timeout)
    assert res.ok
    assert len(res.content) >= 1000
    return res.content


def main():
    """Download inspection PDFs."""
    with open("data/fetched/inspections.csv") as f:
        reports = list(csv.DictReader(f))

    for i, report in enumerate(reports):
        link = report["reportLink"].strip()

        if not link:
            continue

        dest = Path(f"pdfs/inspections{hash_id_from_url(link)}.pdf")
        if dest.exists():
            continue
        else:
            sys.stderr.write(f"Fetching {i:05d}: {link}\n")
            content = fetch(link)
            with open(dest, "wb") as f:
                f.write(content)


if __name__ == "__main__":
    main()
