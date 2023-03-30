import typing
import argparse
import sys
import os
import re
from operator import itemgetter
from pathlib import Path
import pdfplumber



def get_report_text(pages: list[pdfplumber.page.Page], layout: str) -> dict[str, typing.Any]:
    # Exclude species pages
    # Extract text based on layout

    def is_header_char(obj: dict[str, typing.Any]) -> bool:
        return "Bold" in obj.get("fontname", "") and obj.get("size", 0) > 11

    def is_species_page(page: pdfplumber.page.Page) -> bool:
        return page.filter(is_header_char).extract_text().strip() == "Species Inspected"
    
    pages = list(filter(lambda x: not is_species_page(x),pages))

    if layout == "b":

        for i,page in enumerate(pages):
            if i==0:
                pages[i] = page.crop((0,229,page.width,636))
            else:
                pages[i] = page.crop((0,103,page.width,636))

    else:
        for i,page in enumerate(pages):
            if i==0:
                pages[i] = page.crop((0,232,page.width,708))
            else:
                pages[i] = page.crop((0,92,page.width,708))

    return pages


    


        
if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path")
    parser.add_argument("layout")


    args = parser.parse_args()
    file = Path(args.file_path)

    with pdfplumber.open(file) as pdf:
        pages = get_report_text(pdf.pages, args.layout)

        for i, page in enumerate(pages):
            im = page.to_image()
            im.draw_rects(page.edges)
            im.save(f"test{i}.png")

            for j, edge in enumerate(page.edges):
                print(f"Page #{i}, Edge #{j}: {edge['top']}")
        
        




            