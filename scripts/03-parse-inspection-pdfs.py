import argparse
import json
import re
import sys
import typing
from itertools import chain
from operator import itemgetter
from pathlib import Path

import pdfplumber
from pdfplumber.utils import cluster_objects


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

    # There appear to be (at least) three PDF layouts, and the inspection
    # ID formatting seems like a decent way to distinguish between them,
    # so both bits of information are extracted in this step.
    match_a = re.search(r"\b(\d+)\s+Insp_id", top_text)
    if match_a:
        layout = "a" if len(page.lines) < 2 else "b"
        return match_a.group(1), layout
    else:
        match_b = re.search(r"\b(INS-\d+)", top_text)
        if match_b:
            return match_b.group(1), "c"
        else:
            raise Exception(f"Cannot find inspection ID in text: \n{top_text}")


def norm_ws(text: str, newlines: bool = False) -> str:
    text = re.sub(r" +", " ", text).strip()
    text = re.sub(r" *\n+ *", "\n" if newlines else " ", text)
    return text


def get_top_section(page: pdfplumber.page.Page, layout: str) -> dict[str, typing.Any]:
    if layout == "a":
        edges = sorted(page.horizontal_edges, key=itemgetter("top", "x0"))
        line_objs = [edges[0], edges[2]]
    else:
        line_objs = [page.lines[0], page.lines[2]]

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


def get_bottom_section(
    page: pdfplumber.page.Page, layout: str
) -> dict[str, typing.Any]:
    bottom_line = page.edges[-1] if layout == "a" else page.lines[1]

    # Extract the bottom
    bottom = page.crop((0, bottom_line["bottom"], page.width, page.height))

    # Extract the section containing the report date and date received
    right = bottom.crop(
        (
            bottom.bbox[0] + bottom.width * 0.75,
            bottom.bbox[1],
            bottom.bbox[2],
            bottom.bbox[3],
        )
    )
    right_text = norm_ws(right.extract_text(layout=True))

    def extract_right(pat: str) -> str:
        m = re.search(pat, right_text)
        if m is None:
            raise Exception(f"No match for {pat}")
        return norm_ws(m.group(1) or "")

    # At present this only extracts the date of the report.  The names and
    # titles of the inspector are in the left-hand section. These could be
    # extracted in the future.

    return {"report_date": extract_right(r"Date: *(\d{1,2}-[A-Za-z]{3}-\d{4})?$")}


def is_header_char(obj: dict[str, typing.Any], size: int = 11) -> bool:
    return "Bold" in obj.get("fontname", "") and obj.get("size", 0) > size


def is_species_page(page: pdfplumber.page.Page) -> bool:
    return page.filter(is_header_char).extract_text().strip() == "Species Inspected"


def get_separators(
    page: pdfplumber.page.Page, layout: str
) -> list[dict[str, typing.Any]]:
    if layout == "a":
        clustered = cluster_objects(
            [r for r in page.horizontal_edges if r["width"] > 400],
            "top",
            tolerance=5,
        )
        return [c[0] for c in clustered]
    else:
        return sorted(page.lines, key=itemgetter("top"))


class Citation:
    heading: str = ""
    desc: str = ""
    narrative: str = ""

    def add_heading(self, text: str) -> None:
        assert not self.heading
        assert not self.desc
        assert not self.narrative
        self.heading = text

        match = re.search(r"^(\d+[^ ]+)\s*?(Direct|Critical)?\s*(Repeat)?$", text, re.I)
        if not match:
            raise Exception(text)
        self.code, self.kind, self.status = match.groups()

    def add_desc(self, text: str) -> None:
        assert self.heading
        assert not self.narrative
        self.desc += " " + text

    def add_bolded(self, text: str) -> None:
        if not self.heading:
            self.add_heading(text)
        else:
            self.add_desc(text)

    def add_narrative(self, text: str) -> None:
        assert self.heading
        assert self.desc
        self.narrative += "\n" + text

    def to_dict(self) -> dict[str, typing.Union[str, bool]]:
        return dict(
            code=self.code,
            kind=(self.kind or "").strip().title(),
            repeat=bool(self.status),
            desc=self.desc.strip(),
            narrative=self.narrative.strip(),
        )


def get_report_body(
    pages: list[pdfplumber.page.Page], layout: str
) -> tuple[list[dict[str, typing.Union[str, bool]]], str]:
    full_text: list[str] = []
    citations: list[Citation] = []
    for i, page in enumerate(pages):
        separators = get_separators(page, layout)
        bbox = (0, separators[-2]["bottom"], page.width, separators[-1]["top"])
        cropped = page.crop(bbox)

        words = cropped.extract_words(extra_attrs=["size", "fontname"])
        for line_words in cluster_objects(words, "top", tolerance=0):
            first = line_words[0]
            text = " ".join(x["text"] for x in line_words)
            addl = text.lower().strip(":") in [
                "additional inspectors",  # Generic edge-case
                "direct",  # Specific edge-case from hash_id:0db69ec135a5b244
            ]

            if "Bold" in first["fontname"] and not addl:
                if not len(citations):
                    citations.append(Citation())

                if citations[-1].narrative:
                    citations.append(Citation())

                citations[-1].add_bolded(text)
            else:
                if len(citations):
                    citations[-1].add_narrative(text)

        full_text.append(cropped.extract_text().strip())

    return ([v.to_dict() for v in citations], "\n\n".join(full_text))


def get_species(
    pages: list[pdfplumber.page.Page], layout: str
) -> tuple[typing.Optional[int], list[dict[str, typing.Any]]]:
    species = []

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

    pages_by_kind: dict[str, list[pdfplumber.page.Page]] = {"main": [], "species": []}
    for page in pages:
        kind = "species" if is_species_page(page) else "main"
        pages_by_kind[kind].append(page)

    insp_id, layout = get_inspection_id_and_layout(pages[0])
    top_section = get_top_section(pages[0], layout)
    bottom_section = get_bottom_section(pages[0], layout)
    citations, narrative = get_report_body(pages_by_kind["main"], layout)
    animals_total, species = get_species(pages_by_kind["species"], layout)

    return {
        "insp_id": insp_id,
        "layout": layout,
        **top_section,
        **bottom_section,
        **dict(
            citations=citations,
            narrative=narrative,
            animals_total=animals_total,
            species=species,
        ),
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
