"""Upload PDFs to DocumentCloud."""
import csv
import json
import os
import time
import typing
from pathlib import Path

from documentcloud import DocumentCloud
from documentcloud.exceptions import APIError
from retry import retry

# Set directories we'll use
THIS_DIR = Path(__file__).parent.absolute()
ROOT_DIR = THIS_DIR.parent
CACHE_DIR = ROOT_DIR / "data" / "doccloud" / "inspections"
PDF_DIR = ROOT_DIR / "pdfs" / "inspections"


def main():
    """Upload all local PDFs not yet posted to DocumentCloud."""

    # Get everything that's been uploaded already
    with open("data/fetched/inspections.csv") as f:
        fetched_data = list(csv.DictReader(f))

    with open("data/parsed/inspections.json") as f:
        parsed_data = json.load(f)

    # Get all the local PDFs
    print(f"{len(parsed_data)} parsed documents found locally")

    # Loop through all the local PDFs
    for insp in fetched_data:
        # Pull out the file name
        hash_id = insp["hash_id"]
        insp_parsed = parsed_data.get(hash_id)

        # Skip anything we haven't yet parsed
        if insp_parsed is None:
            continue

        cache_path = CACHE_DIR / f"{hash_id}.json"

        # Skip anything we've uploaded already
        if cache_path.exists():
            continue

        # Upload stuff that isn't there
        dc_url, is_new = upload_pdf(PDF_DIR / f"{hash_id}.pdf", insp_parsed["insp_id"])

        # Record that we've uploaded it
        with open(cache_path, "w") as f:
            json.dump(dict(url=dc_url), f, indent=2)

        # Take a little nap
        time.sleep(0.25)


def get_documentcloud_client():
    """Initialize and return a DocumentCloud client that's ready to use."""
    return DocumentCloud(
        os.getenv("DOCUMENTCLOUD_USER"), os.getenv("DOCUMENTCLOUD_PASSWORD")
    )


@retry(tries=10, delay=30)
def upload_pdf(
    pdf_path: Path, insp_id: str, verbose: bool = True
) -> tuple[typing.Optional[str], bool]:
    """Upload the provided object's PDF to DocumentCloud.

    Returns tuple with document URL and boolean indicating if it was uploaded.
    """
    # Make sure it exists
    assert pdf_path.exists()

    # Connect to DocumentCloud
    client = get_documentcloud_client()

    # Search to see if it's already up there
    project_id = os.getenv("DOCUMENTCLOUD_PROJECT_ID")
    assert project_id
    query = f"+project:{project_id} AND data_uid:{pdf_path.stem}"
    search = client.documents.search(query)

    # If it is, we're done
    if len(list(search)) > 0:
        if verbose:
            print(f"{pdf_path.stem} already uploaded")
        return search[0].canonical_url, False

    # If it isn't, upload it now
    if verbose:
        print(f"Uploading {pdf_path.stem}")
    try:
        document = client.documents.upload(
            pdf_path,
            title=f"APHIS Inspection {insp_id}",
            project=project_id.split("-")[-1],
            access="public",
            data={"uid": pdf_path.stem, "inspection_id": insp_id},
        )
        return document.canonical_url, True
    except APIError as e:
        if verbose:
            print(f"API error {e}")
        return None, False


if __name__ == "__main__":
    main()
