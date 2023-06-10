from lib.aphis import (
    add_hash_ids,
    deduplicate,
    fetch,
    iter_fetch_all,
    set_fwuid,
    update_cache,
    write_results,
)


def main() -> None:
    set_fwuid()

    single_response = fetch(0, {})

    search_total = single_response["totalCount"]
    with open("data/fetched/inspections-search-total.txt", "w") as f:
        f.write(str(search_total))

    first_result = single_response["results"][0]
    with open("data/fetched/columns-returned.txt", "w") as f:
        f.write("\n".join(sorted(first_result.keys())))

    latest = add_hash_ids(deduplicate(iter_fetch_all({}, raise_size_error=False)))
    write_results(latest, "data/fetched/inspections-latest.csv")
    update_cache(latest)


if __name__ == "__main__":
    main()
