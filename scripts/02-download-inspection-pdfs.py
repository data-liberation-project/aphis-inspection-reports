import csv
import re
import sys
from pathlib import Path

import requests

with open("data/fetched/inspections.csv") as f:
    reports = list(csv.DictReader(f))

for i, report in enumerate(reports):
    link = report["reportLink"]

    if not link.strip():
        continue

    link_id = re.search(r"ids=(.*?)&", link).group(1)
    dest = Path(f"pdfs/inspections/{link_id}.pdf")
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
