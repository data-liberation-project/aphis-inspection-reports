import csv
import json
import sys
import typing

import requests
from retry import retry
import urllib3

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
    "fwuid": "tr2UlkrAHzi37ijzEeD2UA",
    "app": "siteforce:communityApp",
    "loaded": {
        ("APPLICATION@markup://" "siteforce:communityApp"): "wlLnZvhAshR7p-QD7LB6JQ",
        (
            "COMPONENT@markup://" "instrumentation:o11yCoreCollector"
        ): "8giBLfYbOC17LwOopJh9VQ",
    },
    "dn": [],
    "globals": {},
    "uad": False,
}


def make_inspection_payload(index, criteria):
    action = {
        "descriptor": "apex://EFL_PSTController/ACTION$doIRSearch_UI",
        "params": {
            "searchCriteria": {"index": index, "numberOfRows": 100, **criteria},
            "getCount": True,
        },
    }

    return {
        "message": '{"actions":[' + json.dumps(action) + "]}",
        "aura.context": json.dumps(AURA_CONTEXT),
        "aura.token": "null",
    }


@retry(tries=10, delay=30)
def fetch(index, criteria, timeout: int = 60) -> typing.Dict:
    """Fetch the desired data via a POST request."""
    res = requests.post(
        AURA_URL,
        headers=HEADERS,
        data=make_inspection_payload(index, criteria),
        verify=False,
        timeout=timeout
    )
    res_data = res.json()["actions"][0]["returnValue"]
    if res_data is None:
        raise ValueError(json.dumps(res.json(), indent=2))
    return res_data


class TooManyResultsError(Exception):
    pass


def iter_fetch_all(criteria, raise_size_error=True):
    data = fetch(0, criteria)
    count = data["totalCount"]
    sys.stderr.write(f"{count} results for {criteria}\n")
    if count >= 2100 and raise_size_error:
        raise TooManyResultsError

    yield from data["results"]
    for i in range(1, 21):
        data = fetch(i, criteria)
        if len(data["results"]):
            yield from data["results"]
        else:
            return


def get_sort_key(r):
    return (
        int(r.get("customerNumber", -1)),
        r.get("certNumber", ""),
        r.get("inspectionDate", ""),
        r.get("legalName", ""),
        r.get("siteName", ""),
        r.get("reportLink", ""),
    )


def deduplicate(result_list):
    seen_keys = set()
    unique = []
    for item in result_list:
        key = get_sort_key(item)
        if key in seen_keys:
            continue
        else:
            seen_keys.add(key)
            unique.append(item)
    return sorted(unique, key=get_sort_key)


def write_results(results, dest):
    with open(dest, "w") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
