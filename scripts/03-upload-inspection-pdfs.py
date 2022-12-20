"""Upload PDFs to DocumentCloud."""
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
PDF_DIR = ROOT_DIR / "pdfs" / "inspections"


def main():
    """Upload all local PDFs not yet posted to DocumentCloud."""
    # Get everything that's been uploaded already
    uploaded_list = get_uploaded_pdfs()
    print(f"{len(uploaded_list)} documents found on DocumentCloud")

    # Get all the local PDFs
    local_list = list(PDF_DIR.glob("*.pdf"))
    print(f"{len(local_list)} documents found locally")

    # Loop through all the local PDFs
    for p in local_list:
        # Pull out the file name
        name = f"{p.stem}.pdf"

        # Skip anything we've uploaded already
        if name in uploaded_list:
            continue

        # Upload stuff that isn't there
        upload_pdf(f"{p.stem}.pdf")

        # Take a little nap
        time.sleep(0.25)


def get_documentcloud_client():
    """Initialize and return a DocumentCloud client that's ready to use."""
    return DocumentCloud(
        os.getenv("DOCUMENTCLOUD_USER"), os.getenv("DOCUMENTCLOUD_PASSWORD")
    )


def get_uploaded_pdfs():
    """Retreive a list of document file names that have been uploaded already."""
    client = get_documentcloud_client()
    project_id = os.getenv("DOCUMENTCLOUD_PROJECT_ID")
    assert project_id
    project = client.projects.get(id=project_id)
    document_list = project.document_list
    return [d.data["uid"][0] for d in document_list]


@retry(tries=10, delay=30)
def upload_pdf(
    pdf_name: str, verbose: bool = True
) -> tuple[typing.Optional[str], bool]:
    """Upload the provided object's PDF to DocumentCloud.

    Returns tuple with document URL and boolean indicating if it was uploaded.
    """
    # Get PDF path
    pdf_path = PDF_DIR / pdf_name

    # Make sure it exists
    assert pdf_path.exists()

    # Connect to DocumentCloud
    client = get_documentcloud_client()

    # Search to see if it's already up there
    project_id = os.getenv("DOCUMENTCLOUD_PROJECT_ID")
    assert project_id
    query = f"+project:{project_id} AND data_uid:{pdf_name}"
    search = client.documents.search(query)

    # If it is, we're done
    if len(list(search)) > 0:
        if verbose:
            print(f"{pdf_name} already uploaded")
        return search[0].canonical_url, False

    # If it isn't, upload it now
    if verbose:
        print(f"Uploading {pdf_path}")
    try:
        document = client.documents.upload(
            pdf_path,
            title=f"{pdf_name.replace('.pdf', '')}",
            project=project_id.split("-")[-1],
            access="public",
            data={"uid": pdf_name},
        )
        return document.canonical_url, True
    except APIError as e:
        if verbose:
            print(f"API error {e}")
        return None, False


if __name__ == "__main__":
    main()
