import csv
from datetime import datetime
from pathlib import Path

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
        r["web_discovered"] = datetime.fromisoformat(r["web_discovered"])

    # Sort reverse chron
    sorted_data = sorted(fetched_data, key=lambda x: x["web_discovered"], reverse=True)

    # Slice the most recent 50 for inclusion in our feed
    feed_data = sorted_data[:50]

    # Create our feed object
    fg = FeedGenerator()
    fg.title("Lastest APHIS inpections")
    fg.link(href="https://github.com/data-liberation-project/aphis-inspection-reports")
    fg.description(
        "The latest inspections posted online by the U.S. Department of Agriculture's Animal and Plant Health Inspection Service"  # noqa: E501
    )

    # Add our feed entries
    for row in reversed(feed_data):
        fe = fg.add_entry()
        fe.id(row["web_hash_id"])
        fe.title(f"{row['web_legalName']} ({row['web_inspectionDate']})")
        fe.link(href=row["doccloud_url"])
        fe.description(
            f"""Critical: {row['web_critical']}
Not critical: {row['web_nonCritical']}
Teachable moments: {row['web_teachableMoments']}

Discovered on {row['web_discovered']}
"""
        )

    # Write it out
    fg.rss_file(DATA_DIR / "combined" / "latest-inspections.rss", pretty=True)


if __name__ == "__main__":
    main()
