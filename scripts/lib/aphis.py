import csv
import hashlib
import json
import logging
import re
import typing
from datetime import datetime, timezone
from operator import itemgetter
from pathlib import Path

import requests
import urllib3
from retry import retry

urllib3.disable_warnings()

AURA_URL = "https://efile.aphis.usda.gov/PublicSearchTool/s/sfsites/aura"

HEADERS = {
    "User-Agent": "The Data Liberation Project (data-liberation-project.org)",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "Origin": "https://efile.aphis.usda.gov",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

AURA_CONTEXT = {
    "mode": "PROD",
    "app": "siteforce:communityApp",
    "loaded": {
        ("APPLICATION@markup://" "siteforce:communityApp"): "11hSeJMz5y2BtbPLHOZFww",
        (
            "COMPONENT@markup://" "instrumentation:o11yCoreCollector"
        ): "tdPw-EhKVwwEbR_9pvC9og",
    },
    "dn": [],
    "globals": {},
    "uad": False,
}

format = "%(levelname)s:%(filename)s:%(lineno)d: %(message)s"
logging.basicConfig(format=format)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@retry(tries=3, delay=30, logger=logger)
def get_fwuid() -> str:
    url = "https://aphis-efile.force.com/PublicSearchTool/s/inspection-reports"
    res = requests.get(url)
    html = res.content.decode("utf-8")
    match = re.search("%22fwuid%22%3A%22([^%]+)%22%2C", html)
    if match is None:
        raise ValueError("Cannot find fwuid.")
    fwuid = match.group(1)
    return fwuid


def set_fwuid() -> None:
    AURA_CONTEXT["fwuid"] = get_fwuid()


def make_inspection_payload(
    index: int, criteria: dict[str, typing.Any]
) -> dict[str, str]:
    action = {
        "descriptor": "apex://EFL_PSTController/ACTION$doIRSearch_UI",
        "params": {
            "searchCriteria": {"index": index, "numberOfRows": 100, **criteria},
            "getCount": True,
        },
    }

    if "fwuid" not in AURA_CONTEXT:
        raise ValueError("fwuid has not yet been set; set via lib.aphis.set_fwuid.")

    return {
        "message": '{"actions":[' + json.dumps(action) + "]}",
        "aura.context": json.dumps(AURA_CONTEXT),
        "aura.token": "null",
    }


class BadResponse(Exception):
    pass


@retry(
    exceptions=(BadResponse, requests.exceptions.JSONDecodeError),
    tries=10,
    delay=30,
    logger=logger,
)
def fetch(
    index: int, criteria: dict[str, typing.Any], timeout: int = 60
) -> dict[str, typing.Any]:
    """Fetch the desired data via a POST request."""
    res = requests.post(
        AURA_URL,
        headers=HEADERS,
        data=make_inspection_payload(index, criteria),
        verify=False,
        timeout=timeout,
    )
    decoded = res.content.decode("utf-8")
    if re.search(r"Framework has been updated. Expected:", decoded):
        raise ValueError("FWUID needs updating")

    res_data: typing.Optional[dict[str, str]] = res.json()["actions"][0]["returnValue"]
    if res_data is None:
        raise BadResponse(json.dumps(res.json(), indent=2))
    return res_data


class TooManyResultsError(Exception):
    pass


def iter_fetch_all(
    criteria: dict[str, typing.Any], raise_size_error: bool = True
) -> typing.Generator[dict[str, str], None, None]:
    data = fetch(0, criteria)
    count = data["totalCount"]
    logger.debug(f"{count} results for {criteria}")
    if count >= 2100 and raise_size_error:
        raise TooManyResultsError

    yield from data["results"]
    for i in range(1, 21):
        data = fetch(i, criteria)
        if len(data["results"]):
            yield from data["results"]
        else:
            return


url_id_pat = re.compile(r"&ids=([^&]+)")


def extract_id_from_url(url: str) -> str:
    match = re.search(url_id_pat, url)
    if match is None:
        raise ValueError(
            f"URL does not contain expected `&ids=` pattern; APHIS URL scheme may have changed: {url}"  # noqa: E501
        )
    else:
        return match.group(1)


def get_unique_key(r: dict[str, typing.Any]) -> tuple[str, str, str]:
    url = r.get("reportLink", "")
    url_id = extract_id_from_url(url) if url else ""

    return (
        url_id,
        r["customerNumber"],
        r["inspectionDate"],
    )


def get_sort_key(r: dict[str, typing.Any]) -> tuple[int, str, str, str]:
    return (
        int(r["customerNumber"]),  # Shouldn't ever be missing
        # Note: ? below is a hack to give empty certNumbers lower
        # sort order than existing ones, since APHIS seems to backfill
        # the certNumber once licensed.
        (r.get("certNumber") or "?"),  # Sometimes missing
        r["inspectionDate"],  # Shouldn't ever be missing
        r.get("reportLink", ""),  # Sometimes missing
    )


def deduplicate(
    result_list: list[dict[str, typing.Any]]
) -> list[dict[str, typing.Any]]:
    seen_keys = set()
    unique = []
    for item in sorted(result_list, key=get_sort_key):
        unique_key = get_unique_key(item)
        if unique_key in seen_keys:
            continue
        else:
            seen_keys.add(unique_key)
            unique.append(item)
    return unique


def write_results(results: list[dict[str, typing.Any]], dest: Path) -> None:
    with open(dest, "w") as f:
        writer = csv.DictWriter(
            f, fieldnames=list(results[0].keys()), extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(results)


def hash_id_from_url(url: typing.Optional[str]) -> str:
    if url is None or not url.strip():
        return ""
    else:
        b = extract_id_from_url(url).encode("utf-8")
        return hashlib.sha1(b).hexdigest()[:16]


def add_hash_ids(
    result_list: list[dict[str, typing.Any]]
) -> list[dict[str, typing.Any]]:
    return [
        (
            dict(**res, **{"hash_id": hash_id_from_url(res.get("reportLink"))})
            if "hash_id" not in res
            else res
        )
        for res in result_list
    ]


DEFAULT_CACHE_PATH = Path("data") / "fetched" / "inspections.csv"


def update_cache(
    results_to_add: list[dict[str, typing.Any]],
    cache_path: Path = DEFAULT_CACHE_PATH,
) -> None:
    """
    Update CSV containing all historically-observed inspections
    """
    # Get the current time for datestamping
    now = datetime.now(timezone.utc).replace(microsecond=0)

    # Load cache
    with open(cache_path) as f:
        previous = list(csv.DictReader(f)) if cache_path.exists() else []

    # Build hash_id->discovered dict from cache
    timestamps = dict(map(itemgetter("hash_id", "discovered"), previous))

    # Loop through all proposed additions
    for entry in results_to_add:
        # Use previous value for discovered if exists, else `now`
        entry["discovered"] = timestamps.get(entry["hash_id"], now)

    # Write back to file
    combined = deduplicate(results_to_add + previous)
    write_results(combined, cache_path)
