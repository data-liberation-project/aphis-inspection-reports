import typing
import argparse
import sys
import os
import re
from pathlib import Path
import pdfplumber

def norm_ws(text: str, newlines: bool = False) -> str:
    text = re.sub(r" +", " ", text).strip()
    text = re.sub(r" *\n+ *", "\n" if newlines else " ", text)
    return text

def get_report_text(pages: list[pdfplumber.page.Page], layout: str) -> dict[str, typing.Any]:
    # Exclude species pages
    # Extract text based on layout

    def is_header_char(obj: dict[str, typing.Any]) -> bool:
        return "Bold" in obj.get("fontname", "") and obj.get("size", 0) > 11

    def is_species_page(page: pdfplumber.page.Page) -> bool:
        return page.filter(is_header_char).extract_text().strip() == "Species Inspected"
    
    pages = list(filter(lambda x: not is_species_page(x),pages))
    text = str()

    if len(pages[0].lines) > 2:
        # handle layout 'b'
        for i, page in enumerate(pages):
            if i==0:
                page = page.crop((0,237,page.width,636))
            else:
                page = page.crop((0,103,page.width,636))
            
            text = "".join((text, page.extract_text()))

    else:
        # handle layout 'a'
        for i,page in enumerate(pages):
            if i==0:
                page = page.crop((0,232,page.width,708))
            else:
                page = page.crop((0,92,page.width,708))

            text = "".join((text, page.extract_text()))

    return text


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path")

    args = parser.parse_args()
    directory = Path(args.file_path)

    for file in directory.glob('*'):
        if Path(f"corpus/{file.name}").exists():
            continue
        with pdfplumber.open(file) as pdf:
            
            text = get_report_text(pdf.pages,"a")
            text = norm_ws(text,newlines=True)

            with open(f"corpus/{file.stem}.txt","w+") as output:
                try:
                    output.write(text)
                except UnicodeEncodeError:
                    print(f"Had trouble with characters file in {file.name}")
                    output.write("Could not extract full file contents due to Unicode Encoding Error")
                    




            