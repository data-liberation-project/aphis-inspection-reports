import csv
import hashlib
import sys
import time
from pathlib import Path

import requests


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

        link_hash = hashlib.sha1(link.encode("utf-8")).hexdigest()[:16]
        dest = Path(f"pdfs/inspections/{link_hash}.pdf")
        if dest.exists():
            continue
        else:
            sys.stderr.write(f"Fetching {i:05d}: {link}\n")
            content = fetch(link)
            with open(dest, "wb") as f:
                f.write(content)


if __name__ == "__main__":
    main()
