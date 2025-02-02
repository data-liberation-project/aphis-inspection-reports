import csv
import string
import typing
from itertools import chain
from multiprocessing import Pool
from pathlib import Path

from lib.aphis import (
    TooManyResultsError,
    add_hash_ids,
    deduplicate,
    iter_fetch_all,
    set_fwuid,
    update_cache,
    write_results,
)


def iter_char(
    init_criteria: dict[str, typing.Any]
) -> typing.Generator[dict[str, str], None, None]:
    base = init_criteria.get("customerName", "")

    chars = list(string.ascii_lowercase) + list(string.digits) + list(" ,.&-")

    for char in chars:
        new_chars = base + char

        # Don't search space-only string
        if not new_chars.strip():
            continue

        new_criteria = {**init_criteria, **dict(customerName=new_chars)}

        try:
            yield from iter_fetch_all(new_criteria)
        except TooManyResultsError:
            yield from deduplicate(iter_char(new_criteria))


def fetch_for_letter(letter: str) -> None:
    set_fwuid()
    dest = Path(f"data/fetched/inspections-by-letter/{letter}.csv")
    if dest.exists():
        return

    results = add_hash_ids(deduplicate(iter_char({"customerName": letter})))
    write_results(results, dest)


def main() -> None:
    with Pool(processes=6) as pool:
        pool.map(fetch_for_letter, string.ascii_lowercase)

    paths = Path("data/fetched/inspections-by-letter/").glob("*.csv")

    merged = add_hash_ids(
        deduplicate(chain.from_iterable(csv.DictReader(open(path)) for path in paths))
    )

    write_results(merged, "data/fetched/inspections-by-letter.csv")
    update_cache(merged)


if __name__ == "__main__":
    main()
