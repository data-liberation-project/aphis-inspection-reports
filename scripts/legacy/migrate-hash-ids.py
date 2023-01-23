import csv
import sys
from pathlib import Path

# Not proud of this, but currently seems like the simplest solution
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))
from aphis import add_hash_ids, deduplicate, write_results  # noqa: E402

with open("data/manual/legacy-hash-id-crosswalk.csv") as f:
    xwalk = list(csv.DictReader(f))

TEMPLATES = {
    "pdfs": "pdfs/inspections/{}.pdf",
    "doccloud": "data/doccloud/inspections/{}.json",
    "parsed": "data/parsed/inspections/{}.json",
}

for entry in xwalk:
    id_legacy = entry["hash_url_full"]
    id_new = entry["hash_url_id"]
    for kind, tmpl in TEMPLATES.items():
        src = Path(tmpl.format(id_legacy))
        if src.exists():
            print(f"Moving {kind}: {id_legacy} -> {id_new}")
            dest = Path(tmpl.format(id_new))
            src.rename(dest)

for root in ["data/fetched/inspections-by-letter/", "data/fetched/"]:
    for path in Path(root).glob("*.csv"):
        print(f"Updating hashes in {path}")
        with open(path) as f:
            legacy = list(csv.DictReader(f))

        if "hash_id" in legacy[0]:
            for report in legacy:
                del report["hash_id"]

            updated = add_hash_ids(deduplicate(legacy))
            write_results(updated, path)
