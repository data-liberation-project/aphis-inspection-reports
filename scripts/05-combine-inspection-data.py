"""Combine inspection data from web, PDF parsing, and DocumentCloud."""
import csv
import json
import typing
from pathlib import Path

# Set directories we'll use
THIS_DIR = Path(__file__).parent.absolute()
DATA_DIR = THIS_DIR.parent / "data"


def make_converter(
    prefix: str, to_skip: list[str]
) -> typing.Callable[[dict[str, typing.Any]], dict[str, typing.Any]]:
    def converter(orig: dict[str, typing.Any]) -> dict[str, typing.Any]:
        return {
            f"{prefix}_{key}": val for key, val in orig.items() if key not in to_skip
        }

    return converter


convert_fetched = make_converter(
    "web", ["inspectionDateString"]  # Duplicative of `inspectionDate`
)

convert_parsed = make_converter("pdf", ["species"])
convert_doccloud = make_converter("doccloud", [])


def main() -> None:
    # Get web-fetched data
    with open(DATA_DIR / "fetched" / "inspections.csv") as f:
        fetched_data = list(csv.DictReader(f))

    # Get data parsed from PDFs
    with open(DATA_DIR / "parsed" / "inspections.json") as f:
        parsed_data = json.load(f)

    # Get DocCloud URLs
    with open(DATA_DIR / "doccloud" / "inspections.json") as f:
        doccloud_data = json.load(f)

    all_species = []

    with open(DATA_DIR / "combined" / "inspections.csv", "w") as f:
        fieldnames = (
            list(convert_fetched(fetched_data[0]).keys())
            + list(convert_parsed(parsed_data[next(iter(parsed_data))]).keys())
            + list(convert_doccloud(doccloud_data[next(iter(doccloud_data))]).keys())
            # Add derived columns
            + ["licenseType"]
        )
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for fetched in fetched_data:
            hash_id = fetched["hash_id"]

            parsed = parsed_data.get(hash_id, {})

            if hash_id:
                for s in parsed["species"]:
                    if s["scientific"].upper() == "NONE" and s["count"] == 0:
                        continue
                    all_species.append({"hash_id": hash_id, **s})

            doccloud = doccloud_data.get(hash_id, {"url": ""})

            c = {
                **convert_fetched(fetched),
                **convert_parsed(parsed),
                **convert_doccloud(doccloud),
            }

            # Parse the license type identifier out of the certification number
            if c["web_certNumber"]:
                parts = c["web_certNumber"].split("-")
                c["licenseType"] = parts[1]
            else:
                c["licenseType"] = None

            writer.writerow(c)

    with open(DATA_DIR / "combined" / "inspections-species.csv", "w") as f:
        fieldnames = ["hash_id", "count", "scientific", "common"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_species)


if __name__ == "__main__":
    main()
