import typing
import argparse
import sys
sys.path.append('../scripts')
import os   
import re
from pathlib import Path
import pdfplumber
from importlib import import_module
import random

parse_inspection_pdfs = import_module('03-parse-inspection-pdfs')



def norm_ws(text: str, newlines: bool = False) -> str:
    text = re.sub(r" +", " ", text).strip()
    text = re.sub(r" *\n+ *", "\n" if newlines else " ", text)
    return text

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path")

    args = parser.parse_args()
    directory = list(Path(args.file_path).iterdir())
    
    for _ in range(250):

        file = random.choice(directory)

        with pdfplumber.open(file) as pdf:
            
            text = parse_inspection_pdfs.get_report_body(pdf.pages,"layout")
            content = norm_ws(text['content'],newlines=True)

            if text['violations']:

                print(file.name, text['violations'])  



            