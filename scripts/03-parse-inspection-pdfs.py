import argparse
import json
import re
import sys
import typing
from itertools import chain
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
        "--start",
        type=int,
        help="Only start parsing the {n}th PDF. Mainly useful for testing new parsing code.",  # noqa: E501
    )
    parser.add_argument(
        "--test",
        type=str,
        help="Test parsing against a single PDF, writing results to stdout.",
    )
    return parser.parse_args()


def get_inspection_id_and_layout(page: pdfplumber.page.Page) -> tuple[str, str]:
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


def get_top_section(page: pdfplumber.page.Page, layout: str) -> dict[str, typing.Any]:
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
        "customer_id": extract_right(r"Customer ID: *(\d+)"),
        "customer_name": left_text.split("\n")[0],
        "customer_addr": "\n".join(left_text.split("\n")[1:]),
        "certificate": extract_right(
            r"Certificate: *(\d+-[A-Z]+-\d+|--|Open Application)? *\n"
        ),
        "site_id": extract_right(r"Site: *([^\n]*) *\n"),
        "site_name": norm_ws(right_text_small),
        "insp_type": extract_right(r"Type: *([A-Z\-#\s\d]+?)Date:"),
        "date": extract_right(r"Date: *(\d{1,2}-[A-Za-z]{3}-\d{4})"),
    }

def get_bottom_section(page: pdfplumber.page.Page, layout:str) -> dict[str, typing.Any]:
    if len(page.lines)>1:
        bottom_line = page.lines[1]
    else:
        bottom_line = page.edges[-1]

    # Extract the bottom
    bottom = page.crop((0, bottom_line['bottom'], page.width,page.height))

    # Extract the section containing the report date and date received
    right = bottom.crop((bottom.bbox[0]+bottom.width*0.75,bottom.bbox[1],bottom.bbox[2],bottom.bbox[3]))
    right_text = norm_ws(right.extract_text(layout=True))

    def extract_right(pat:str) -> str:
        m = re.search(pat, right_text)
        if m is None:
            raise Exception(f"No match for {pat}")
        return norm_ws(m.group(1) or "")
    
    # At present this only extracts the date of the report. 
    # The names and titles of the inspector are in the left-hand section. These could be extracted in the future.

    return {
        'report_date': extract_right(r"Date: *(\d{1,2}-[A-Za-z]{3}-\d{4})")
    }


def get_species(
    pages: list[pdfplumber.page.Page], layout: str
) -> tuple[typing.Optional[int], list[dict[str, typing.Any]]]:
    species = []

    def is_header_char(obj: dict[str, typing.Any]) -> bool:
        return "Bold" in obj.get("fontname", "") and obj.get("size", 0) > 11

    def is_species_page(page: pdfplumber.page.Page) -> bool:
        return page.filter(is_header_char).extract_text().strip() == "Species Inspected"

    def get_table_chars(
        chars: list[dict[str, typing.Any]]
    ) -> list[dict[str, typing.Any]]:
        # There appear to be two main underlying structures of the
        # species-table lists, although they appear largely similar to the
        # human eye.
        char_texts = "".join(c["text"][0] for c in chars)
        match = re.search(
            r"Page \d+ of \d+ +(Count Scientific Name Common Name )?(?P<table>.*)$",
            char_texts,
        )
        if match:
            return chars[match.start("table") : match.end("table")]
        else:
            chars_sorted = sorted(chars, key=itemgetter("top", "x0"))
            char_texts = "".join(c["text"][0] for c in chars_sorted)
            match = re.search(
                r"(Count *Scientific *Name *Common *Name *)(?P<table>.*)Page (\d+|\{cp\}) of \d+ *$",  # noqa: E501
                char_texts,
            )
            assert match, "Unrecognized char/layout structure"
            return chars_sorted[match.start("table") : match.end("table")]

    def parse_species_page(
        page: pdfplumber.page.Page,
    ) -> list[tuple[int, str, str]]:
        rows = [[""]]
        last_char = None

        table_chars = get_table_chars(page.chars)

        if not len(table_chars):
            return []

        for char in table_chars:
            if last_char is None:
                dist = 0
            else:
                dist = char["x0"] - last_char["x1"]
            # If starting a new row
            if dist < -200 or last_char is None:
                # Append and pad out previous row
                if last_char is not None:
                    remaining = 3 - len(rows[-1])
                    rows[-1] += [""] * remaining
                # If starting at very beginning (typical)
                if char["x0"] < 50:
                    rows.append([char["text"]])
                # Otherwise, consider the first cell blank
                else:
                    rows.append(["", char["text"]])
            # If starting a new column (i.e., jumping right)
            if last_char and dist > 5:
                rows[-1].append(char["text"])
            # If continuing the current chunk of text
            else:
                rows[-1][-1] += char["text"]
            last_char = char

        remaining = 3 - len(rows[-1])
        rows[-1] += [""] * remaining

        def has_data(row: list[str]) -> bool:
            return bool(row[0].strip())

        rows_with_data = filter(has_data, rows)
        return [(int(a.strip()), b.strip(), c.strip()) for a, b, c in rows_with_data]

    species_pages = list(filter(is_species_page, pages))
    assert len(species_pages) > 0

    rows_all = list(chain(*map(parse_species_page, species_pages)))
    if not rows_all:
        # Make sure we didn't just fail to grab the table
        assert re.search(r"\d+\s+Total", species_pages[0].extract_text()) is None
        return None, []

    assert rows_all[-1][1] == "Total"  # Make sure last row is the total

    species_rows = rows_all[:-1]
    animals_total = sum(a for a, b, c in species_rows)
    assert (
        animals_total == rows_all[-1][0]
    )  # Make sure the species totals sum to the overall total

    species = [dict(count=a, scientific=b, common=c) for a, b, c in species_rows]
    return animals_total, species


def prep_page(page: pdfplumber.page.Page) -> pdfplumber.page.Page:
    return page.dedupe_chars().filter(lambda obj: obj.get("text") != "(cid:9)")


def parse(pdf: pdfplumber.pdf.PDF) -> dict[str, typing.Any]:
    pages = list(map(prep_page, pdf.pages))
    insp_id, layout = get_inspection_id_and_layout(pages[0])
    top_section = get_top_section(pages[0], layout)
    bottom_section = get_bottom_section(pages[0],layout)
    animals_total, species = get_species(pages, layout)
    return {
        "insp_id": insp_id,
        "layout": layout,
        **top_section,
        **bottom_section,
        **dict(animals_total=animals_total, species=species),
    }


def parse_all(overwrite: bool = False, start: typing.Optional[int] = 0) -> None:
    paths = sorted(Path("pdfs/inspections/").glob("*.pdf"))
    start_int = start or 0
    for i, path in enumerate(paths):
        if i < start_int:
            continue

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
        parse_all(overwrite=args.overwrite, start=args.start)
        combine()


if __name__ == "__main__":
    main()
