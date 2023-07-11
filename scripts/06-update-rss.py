import csv
import typing
from datetime import datetime, timezone
from itertools import groupby
from operator import itemgetter
from pathlib import Path

from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator

# Set directories we'll use
THIS_DIR = Path(__file__).parent.absolute()
DATA_DIR = THIS_DIR.parent / "data"

with open(DATA_DIR / "manual" / "states.csv") as f:
    STATES = sorted(set([row["abbr"] for row in csv.DictReader(f)]))


def main() -> None:
    # Get data
    with open(DATA_DIR / "combined" / "inspections.csv") as f:
        fetched_data = list(csv.DictReader(f))

    # Parse dates
    for r in fetched_data:
        r["discovered"] = datetime.fromisoformat(r["discovered"])

    sorted_data = sorted(
        fetched_data,
        key=itemgetter("discovered", "web_inspectionDate", "hash_id"),
        reverse=True,
    )

    for state in [None] + STATES:
        all_reports = (
            [x for x in sorted_data if x["customer_state"] == state]
            if state
            else sorted_data
        )
        critical_reports = [
            d for d in all_reports if int(d["web_critical"]) or int(d["web_direct"])
        ]
        state_text = f" of {state} customers" if state else ""
        dest_dir = (
            DATA_DIR / "combined" / "state-feeds" if state else DATA_DIR / "combined"
        )
        fn_prefix = f"{state.lower()}-" if state else ""

        # Create our full feed
        full_feed = generate_feed(
            all_reports,
            title=f"Latest APHIS inspections{state_text}",
            desc=f"The latest inspections{state_text} posted online by the U.S. Department of Agriculture's Animal and Plant Health Inspection Service",  # noqa: E501
        )

        full_feed.rss_file(dest_dir / f"{fn_prefix}latest-inspections.rss", pretty=True)

        # Create our critical feed
        critical_feed = generate_feed(
            critical_reports,
            title=f"Latest critical APHIS inspections{state_text}",
            desc=f"The latest inspections{state_text} with critical violations posted online by the U.S. Department of Agriculture's Animal and Plant Health Inspection Service",  # noqa: E501
        )

        critical_feed.rss_file(
            dest_dir / f"{fn_prefix}latest-critical-inspections.rss", pretty=True
        )


def _create_entry(entry: FeedEntry, data: typing.Dict[typing.Any, typing.Any]) -> None:
    entry.id(data["hash_id"])
    entry.title(f"{data['web_legalName']} ({data['web_inspectionDate']})")
    entry.link(href=data["doccloud_url"])
    entry.description(
        f"""Direct: {data['web_direct']}
Other Critical: {data['web_critical']}
Not critical: {data['web_nonCritical']}
Teachable moments: {data['web_teachableMoments']}

Discovered on {data['discovered']}
"""
    )


def generate_feed(
    items: list[dict[str, typing.Any]],
    title: str,
    desc: str,
    # Feed should have all items since X days ago
    min_age_days: int = 3,
    # Feed shouldn't have items older than X days
    max_age_days: int = 30,
    # Feed shouldn't add another chunk beyond min_age_days,
    # if it would mean exceeding X entries
    max_entries: int = 50,
) -> FeedGenerator:
    feed = FeedGenerator()
    feed.title(title)
    feed.link(
        href="https://github.com/data-liberation-project/aphis-inspection-reports"
    )
    feed.description(desc)

    now = datetime.now(timezone.utc)

    for discovered, _group in groupby(items, itemgetter("discovered")):
        group = list(_group)
        age_days = (now - discovered).days
        if age_days <= min_age_days or (
            age_days <= max_age_days and len(group + feed.entry()) <= max_entries
        ):
            for item in group:
                entry = feed.add_entry(order="append")
                _create_entry(entry, item)

    return feed


if __name__ == "__main__":
    main()
