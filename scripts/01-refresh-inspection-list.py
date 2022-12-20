import csv

from lib.aphis import add_hash_ids, deduplicate, fetch, iter_fetch_all, write_results


def main():
    search_total = fetch(0, {})["totalCount"]
    with open("data/fetched/inspections-search-total.txt", "w") as f:
        f.write(str(search_total))

    latest = deduplicate(iter_fetch_all({}, raise_size_error=False))
    write_results(latest, "data/fetched/inspections-latest.csv")

    # Update CSV containing all historically-observed inspections
    previous = list(csv.DictReader(open("data/fetched/inspections.csv")))
    combined = add_hash_ids(deduplicate(latest + previous))
    write_results(combined, "data/fetched/inspections.csv")


if __name__ == "__main__":
    main()
