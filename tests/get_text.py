import typing
import argparse
import sys
sys.path.append('../scripts')
import os   
import re
from pathlib import Path
import pdfplumber
from importlib import import_module

parse_inspection_pdfs = import_module('03-parse-inspection-pdfs')



def norm_ws(text: str, newlines: bool = False) -> str:
    text = re.sub(r" +", " ", text).strip()
    text = re.sub(r" *\n+ *", "\n" if newlines else " ", text)
    return text

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path")

    args = parser.parse_args()
    directory = Path(args.file_path)

    for file in directory.glob('*'):
        if file.suffix != ".pdf":
            continue
        with pdfplumber.open(file) as pdf:
            
            text = parse_inspection_pdfs.get_report_body(pdf.pages,"a")
            content = norm_ws(text['content'],newlines=True)

            print(text['violations'])

            with open(f"../example_reports/test_set/{file.stem}.txt","wb+") as output:
                try:
                    output.write(text['content'].encode('utf-8','replace'))
                except UnicodeEncodeError:
                    print(f"Had trouble with characters file in {file.name}")
                    output.write("Could not extract full file contents due to Unicode Encoding Error")
                    




            