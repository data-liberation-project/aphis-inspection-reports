import csv
from datetime import datetime, timezone

from lib.aphis import (
    add_hash_ids,
    deduplicate,
    fetch,
    get_sort_key,
    iter_fetch_all,
    write_results,
)


def main() -> None:
    search_total = fetch(0, {})["totalCount"]
    with open("data/fetched/inspections-search-total.txt", "w") as f:
        f.write(str(search_total))

    latest = add_hash_ids(deduplicate(iter_fetch_all({}, raise_size_error=False)))
    write_results(latest, "data/fetched/inspections-latest.csv")

    # Read in historically-observed inspections
    with open("data/fetched/inspections.csv", "r") as fp:
        lookup = dict((d["hash_id"], d) for d in csv.DictReader(fp))

    # Get the current time for datestamping
    now = datetime.now(timezone.utc)

    # Loop through all of the newly scraped data
    for d in latest:
        # Get its key
        key = d["hash_id"]
        # If the record is new
        if key not in lookup:
            # Mark the time
            d["discovered"] = now
            # Add it to the lookup
            lookup[key] = d

    # Convert the lookup back into a list
    merged = sorted(lookup.values(), key=get_sort_key)

    # Write it out
    write_results(merged, "data/fetched/inspections.csv")


if __name__ == "__main__":
    main()
