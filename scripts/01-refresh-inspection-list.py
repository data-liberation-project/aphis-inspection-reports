import csv

from lib.aphis import deduplicate, iter_fetch_all, write_results


def main():
    latest = deduplicate(iter_fetch_all({}, raise_size_error=False))
    write_results(latest, "data/fetched/inspections-latest.csv")
    previous = list(csv.DictReader(open("data/fetched/inspections.csv")))
    combined = deduplicate(latest + previous)
    write_results(combined, "data/fetched/inspections.csv")


if __name__ == "__main__":
    main()
