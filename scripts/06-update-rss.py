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

    # Create our full feed
    full_feed = generate_feed(
        sorted_data,
        title="Lastest APHIS inpections",
        desc="The latest inspections posted online by the U.S. Department of Agriculture's Animal and Plant Health Inspection Service",  # noqa: E501
    )

    # Create our critical feed
    critical_feed = generate_feed(
        [d for d in sorted_data if int(d["web_critical"]) > 0],
        title="Lastest critical APHIS inpections",
        desc="The latest inspections with critical violations posted online by the U.S. Department of Agriculture's Animal and Plant Health Inspection Service",  # noqa: E501
    )

    # Write it out
    full_feed.rss_file(DATA_DIR / "combined" / "latest-inspections.rss", pretty=True)
    critical_feed.rss_file(
        DATA_DIR / "combined" / "latest-critical-inspections.rss", pretty=True
    )


def _create_entry(entry: FeedEntry, data: typing.Dict[typing.Any, typing.Any]) -> None:
    entry.id(data["hash_id"])
    entry.title(f"{data['web_legalName']} ({data['web_inspectionDate']})")
    entry.link(href=data["doccloud_url"])
    entry.description(
        f"""Critical: {data['web_critical']}
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
