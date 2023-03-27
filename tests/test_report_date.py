import pdfplumber
import typing
import re

def norm_ws(text: str, newlines: bool = False) -> str:
    text = re.sub(r" +", " ", text).strip()
    text = re.sub(r" *\n+ *", "\n" if newlines else " ", text)
    return text




def get_bottom_section(page: pdfplumber.page.Page, layout:str) -> dict[str, typing.Any]:
    if len(page.lines)>1:
        bottom_line = page.lines[1]
    else:
        bottom_line = page.edges[-1]

    # Extract the bottom
    bottom = page.crop((0, bottom_line['bottom'], page.width,page.height))


    # Extract the section containing the report date
    right = bottom.crop((bottom.bbox[0]+bottom.width*0.75,bottom.bbox[1],bottom.bbox[2],bottom.bbox[3]))
    right_text = norm_ws(right.extract_text(layout=True))

    def extract_right(pat:str) -> str:
        m = re.search(pat, right_text)
        if m is None:
            raise Exception(f"No match for {pat}")
        return norm_ws(m.group(1) or "")
    
    return {
        'report_date': extract_right(r"Date: *(\d{1,2}-[A-Za-z]{3}-\d{4})")
    }


with pdfplumber.open("extract_reportdate_test1.pdf") as pdf:
    format1 = pdf.pages[0]
    bottom1 = get_bottom_section(format1,"a")
    # im = bottom1.to_image()
    # im.draw_vline(bottom1.width*0.75)
    # im.save("test1.png")

with pdfplumber.open("extract_reportdate_test2.pdf") as pdf:
    format2 = pdf.pages[0]
    bottom2 = get_bottom_section(format2,"b")
    # im = bottom2.to_image()
    # im.draw_vline(bottom2.width*0.75)
    # im.save("test2.png")