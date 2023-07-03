"""Download inspection PDFs."""
import csv
from pathlib import Path

import requests
from lib.aphis import hash_id_from_url
from lib.logger import get_logger
from retry import retry

logger = get_logger()


@retry(tries=10, delay=30, logger=logger)
def fetch(link: str, timeout: int = 60) -> bytes:
    """Request the provided URL and return the content."""
    res = requests.get(link, timeout=timeout)
    assert res.ok
    assert len(res.content) >= 1000
    return res.content


def main() -> None:
    """Download inspection PDFs."""
    with open("data/fetched/inspections.csv") as f:
        reports = list(csv.DictReader(f))

    for i, report in enumerate(reports):
        link = report["reportLink"].strip()

        if not link:
            continue

        dest = Path(f"pdfs/inspections/{hash_id_from_url(link)}.pdf")
        if dest.exists():
            continue
        else:
            logger.debug(f"Fetching {i:05d}: {link}")
            content = fetch(link)
            with open(dest, "wb") as f:
                f.write(content)


if __name__ == "__main__":
    main()
