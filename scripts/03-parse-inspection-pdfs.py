import argparse
import json
import re
import sys
import typing
from operator import itemgetter
from pathlib import Path

import pdfplumber


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite cached parsings in parsed/inspections?",
    )
    parser.add_argument(
        "--test",
        type=str,
        help="Test parsing against a single PDF, writing results to stdout.",
    )
    return parser.parse_args()


def get_inspection_id_and_layout(pdf: pdfplumber.pdf.PDF) -> tuple[str, str]:
    page = pdf.pages[0].dedupe_chars()
    edges = sorted(page.edges, key=itemgetter("top", "x0"))
    top = page.crop((0, 0, page.width, edges[0]["top"]))
    top_text = top.extract_text(x_tolerance=2)

    # There appear to be (at least) two PDF layouts, and the inspection ID
    # formatting seems like a decent way to distinguish between them, so
    # both bits of information are extracted in this step.
    match_a = re.search(r"\b(\d+)\s+Insp_id", top_text)
    if match_a:
        return match_a.group(1), "a"
    else:
        match_b = re.search(r"\b(INS-\d+)", top_text)
        if match_b:
            return match_b.group(1), "b"
        else:
            raise Exception(f"Cannot find inspection ID in text: \n{top_text}")


def parse(pdf: pdfplumber.pdf.PDF) -> dict[str, typing.Any]:
    insp_id, layout = get_inspection_id_and_layout(pdf)
    return {
        "insp_id": insp_id,
        "layout": layout,
    }


def parse_all(overwrite: bool = False) -> None:
    paths = sorted(Path("pdfs/inspections/").glob("*.pdf"))
    for i, path in enumerate(paths):
        dest = Path(f"data/parsed/inspections/{path.stem}.json")
        if dest.exists() and not overwrite:
            continue

        print(i, path)
        with pdfplumber.open(path) as pdf:
            results = parse(pdf)
            with open(dest, "w") as f:
                json.dump(results, f, indent=2)


def combine() -> None:
    def load(path: Path) -> tuple[str, dict[str, typing.Any]]:
        with open(path) as f:
            return (path.stem, json.load(f))

    paths = sorted(Path("data/parsed/inspections/").glob("*.json"))
    combined = dict(map(load, paths))
    with open("data/parsed/inspections.json", "w") as f:
        json.dump(combined, f, indent=2)


def main() -> None:
    args = parse_args()
    if args.test:
        with pdfplumber.open(args.test) as pdf:
            results = parse(pdf)
            json.dump(results, sys.stdout, indent=2)
            sys.stdout.write("\n")
    else:
        parse_all(overwrite=args.overwrite)
        combine()


if __name__ == "__main__":
    main()
