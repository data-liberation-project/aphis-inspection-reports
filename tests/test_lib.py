"""Test utilities in the `lib` module."""
from scripts.lib import aphis

RESULTS_EXAMPLE = [
    {
        "certNumber": "93-R-0432",
        "critical": 0,
        "customerNumber": "9191",
        "direct": 0,
        "inspectionDate": "2022-11-14",
        "inspectionDateString": "11/14/2022",
        "legalName": "University of California-Berkeley",
        "nonCritical": 0,
        "reportLink": "https://aphis--c.na21.content.force.com/sfc/dist/version/download/?oid=00Dt0000000GyZH&ids=068t000000gv9b5&d=%2Fa%2Ft0000001ZLeA%2FKg5uHjj9LGi0zJe1NX05AnSW950c7_feljvRekhSHmU&asPdf=false",  # noqa: E501
        "siteName": "UNIVERSITY OF CALIFORNIA, BERKELEY",
        "teachableMoments": 0,
    },
    {
        "certNumber": "93-R-0432",
        "critical": 0,
        "customerNumber": "9191",
        "direct": 0,
        "inspectionDate": "2022-04-12",
        "inspectionDateString": "4/12/2022",
        "legalName": "University of California-Berkeley",
        "nonCritical": 0,
        "reportLink": "https://aphis--c.na21.content.force.com/sfc/dist/version/download/?oid=00Dt0000000GyZH&ids=068t000000Ywc88&d=%2Fa%2Ft0000001QXxq%2FerrBhl3.BQbWN8eQzvew7ClQTZbfvwZizZ5jfOdA5Ek&asPdf=false",  # noqa: E501
        "siteName": "UNIVERSITY OF CALIFORNIA, BERKELEY",
        "teachableMoments": 0,
    },
    {
        "certNumber": "93-R-0432",
        "critical": 0,
        "customerNumber": "9191",
        "direct": 0,
        "inspectionDate": "2022-05-18",
        "inspectionDateString": "5/18/2022",
        "legalName": "University of California-Berkeley",
        "nonCritical": 2,
        "reportLink": "https://aphis--c.na21.content.force.com/sfc/dist/version/download/?oid=00Dt0000000GyZH&ids=068t000000Yx0AL&d=%2Fa%2Ft0000001QZjW%2FFbXeOO.eGu5WMots03W3iQYrp7G5MZRH3B1FILf1RMY&asPdf=false",  # noqa: E501
        "siteName": "UNIVERSITY OF CALIFORNIA, BERKELEY",
        "teachableMoments": 0,
    },
    # Intentional duplicate here for testing
    {
        "certNumber": "93-R-0432",
        "critical": 0,
        "customerNumber": "9191",
        "direct": 0,
        "inspectionDate": "2022-11-14",
        "inspectionDateString": "11/14/2022",
        "legalName": "University of California-Berkeley",
        "nonCritical": 0,
        "reportLink": "https://aphis--c.na21.content.force.com/sfc/dist/version/download/?oid=00Dt0000000GyZH&ids=068t000000gv9b5&d=%2Fa%2Ft0000001ZLeA%2FKg5uHjj9LGi0zJe1NX05AnSW950c7_feljvRekhSHmU&asPdf=false",  # noqa: E501
        "siteName": "UNIVERSITY OF CALIFORNIA, BERKELEY",
        "teachableMoments": 0,
    },
]


def test_hash_id_from_url() -> None:
    """Test the hash_id_from_url utility."""
    link = str(RESULTS_EXAMPLE[0]["reportLink"])
    hash_id = aphis.hash_id_from_url(link)
    assert hash_id == "be2b020ee5ee65c8"


def test_add_hash_ids() -> None:
    """Test the add_hash_ids utility."""
    added = aphis.add_hash_ids(RESULTS_EXAMPLE)

    assert added[0]["hash_id"] == "be2b020ee5ee65c8"

    # Make sure we're not modifying original
    assert "hash_id" not in RESULTS_EXAMPLE[0]

    # Should not raise error when rerunning
    aphis.add_hash_ids(added)


def test_get_sort_key() -> None:
    """Test the get_sort_key utility."""
    key = aphis.get_sort_key(RESULTS_EXAMPLE[0])
    assert key == (
        "9191",
        "93-R-0432",
        "2022-11-14",
        RESULTS_EXAMPLE[0]["reportLink"],
    )


def test_deduplicate() -> None:
    """Test the deduplicate utility."""
    d = aphis.deduplicate(RESULTS_EXAMPLE)
    # Last item in array is intentionally a dupe
    assert sorted(d, key=aphis.get_sort_key) == sorted(
        RESULTS_EXAMPLE[:-1], key=aphis.get_sort_key
    )
