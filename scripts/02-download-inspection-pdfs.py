import csv
import hashlib
import sys
from pathlib import Path

import requests

with open("data/fetched/inspections.csv") as f:
    reports = list(csv.DictReader(f))

for i, report in enumerate(reports):
    link = report["reportLink"]

    if not link.strip():
        continue

    link_hash = hashlib.sha1(link.encode("utf-8")).hexdigest()[:16]
    dest = Path(f"pdfs/inspections/{link_hash}.pdf")
    if dest.exists():
        continue
    else:
        sys.stderr.write(f"Fetching {i:05d}: {link}\n")
        res = requests.get(link)
        if res.status_code == 200:
            with open(dest, "wb") as f:
                f.write(res.content)
        else:
            sys.stderr.write(f"🚨 HTTP error on {link}\n")
