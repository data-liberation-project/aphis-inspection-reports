import csv
from datetime import datetime
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

    # Sort reverse chron
    sorted_data = sorted(fetched_data, key=lambda x: x["discovered"], reverse=True)
    # Create our full feed
    full_feed = FeedGenerator()
    full_feed.title("Lastest APHIS inpections")
    full_feed.link(
        href="https://github.com/data-liberation-project/aphis-inspection-reports"
    )
    full_feed.description(
        "The latest inspections posted online by the U.S. Department of Agriculture's Animal and Plant Health Inspection Service"  # noqa: E501
    )
    # Add our feed entries
    for row in reversed(sorted_data[:50]):
        # Add it to the full feed
        full_entry = full_feed.add_entry()
        _create_entry(full_entry, row)

    # Create our critical feed
    critical_feed = FeedGenerator()
    critical_feed.title("Lastest critical APHIS inpections")
    critical_feed.link(
        href="https://github.com/data-liberation-project/aphis-inspection-reports"
    )
    critical_feed.description(
        "The latest inspections with critical violations posted online by the U.S. Department of Agriculture's Animal and Plant Health Inspection Service"  # noqa: E501
    )
    # Only add critical inspections to the critical feed
    critical_data = [d for d in sorted_data if int(d["web_critical"]) > 0]
    for row in reversed(critical_data[:50]):
        critical_entry = critical_feed.add_entry()
        _create_entry(critical_entry, row)

    # Write it out
    full_feed.rss_file(DATA_DIR / "combined" / "latest-inspections.rss", pretty=True)
    critical_feed.rss_file(
        DATA_DIR / "combined" / "latest-critical-inspections.rss", pretty=True
    )


def _create_entry(entry: FeedEntry, data: dict):
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


if __name__ == "__main__":
    main()
