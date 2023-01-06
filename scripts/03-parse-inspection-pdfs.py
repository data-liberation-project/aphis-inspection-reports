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


def norm_ws(text: str, newlines: bool = False) -> str:
    text = re.sub(r" +", " ", text).strip()
    text = re.sub(r" *\n+ *", "\n" if newlines else " ", text)
    return text


def get_top_section(pdf: pdfplumber.pdf.PDF, layout: str) -> dict[str, typing.Any]:
    page = pdf.pages[0].dedupe_chars()

    if len(page.lines) > 2:
        line_objs = [page.lines[0], page.lines[2]]
    else:
        edges = sorted(page.horizontal_edges, key=itemgetter("top", "x0"))
        line_objs = [edges[0], edges[2]]

    top = page.crop((0, line_objs[0]["top"], page.width, line_objs[1]["top"]))

    left = top.crop(
        (top.bbox[0], top.bbox[1], top.bbox[0] + top.width / 2, top.bbox[3])
    )
    right = top.crop(
        (top.bbox[0] + top.width / 2, top.bbox[1], top.bbox[2], top.bbox[3])
    )

    left_text = norm_ws(left.extract_text(layout=True), newlines=True)
    right_text = right.extract_text(layout=True)
    right_text_small = right.filter(
        lambda o: float(o.get("size", 999)) < 9
    ).extract_text()

    def extract_right(pat: str) -> str:
        m = re.search(pat, right_text)
        if m is None:
            raise Exception(f"No match for {pat}")
        return norm_ws(m.group(1) or "")

    return {
        "customer_id": extract_right(r"Customer ID:\s*(\d+)"),
        "customer_name": left_text.split("\n")[0],
        "customer_addr": "\n".join(left_text.split("\n")[1:]),
        "certificate": extract_right(
            r"Certificate:\s*(\d+-[A-Z]+-\d+|--|Open Application)?\s*\n"
        ),
        "site_id": extract_right(r"Site:\s*([^\n]+)\s*\n"),
        "site_name": norm_ws(right_text_small),
        "insp_type": extract_right(r"Type:\s*([A-Z\-#\s\d]+?)Date:"),
        "date": extract_right(r"Date:\s*(\d{1,2}-[A-Za-z]{3}-\d{4})"),
    }


def parse(pdf: pdfplumber.pdf.PDF) -> dict[str, typing.Any]:
    insp_id, layout = get_inspection_id_and_layout(pdf)
    top_section = get_top_section(pdf, layout)
    return {
        "insp_id": insp_id,
        "layout": layout,
        **top_section,
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
