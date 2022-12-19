import csv
import sys
import time
from pathlib import Path

import requests
from lib.aphis import filename_from_url


def fetch(link):
    while True:
        try:
            res = requests.get(link)
        except Exception as e:
            sys.stderr.write(f"🚨 Exception: {e}\n")
            time.sleep(30)
            continue

        if res.status_code != 200:
            sys.stderr.write(f"🚨 HTTP error on {link}\n")
        elif len(res.content) < 1000:
            sys.stderr.write(f"🚨 Too-small size on {link}\n")
        else:
            return res.content

        time.sleep(30)


def main():
    with open("data/fetched/inspections.csv") as f:
        reports = list(csv.DictReader(f))

    for i, report in enumerate(reports):
        link = report["reportLink"].strip()

        if not link:
            continue

        dest = Path("pdfs/inspections" / filename_from_url(link))
        if dest.exists():
            continue
        else:
            sys.stderr.write(f"Fetching {i:05d}: {link}\n")
            content = fetch(link)
            with open(dest, "wb") as f:
                f.write(content)


if __name__ == "__main__":
    main()
