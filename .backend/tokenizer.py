import pymupdf4llm
import docx2txt
from pptx import Presentation

## File types
def txt(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        raw_content = f.read()
    return apply_preprocessing(raw_content)

def pdf(file_path):
    return apply_preprocessing(pymupdf4llm.to_markdown(file_path))

def docx(file_path):
    return apply_preprocessing(docx2txt.process(file_path))

def pptx(file_path):
    full_string = ""
    prs = Presentation(file_path)
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                full_string += shape.text+"\n"
    return apply_preprocessing(full_string)

def markdown(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        raw_content = f.read()
    return apply_preprocessing(raw_content)

## Processing functions
def remove_special_char(lst):
    return[''.join(e for e in string if e.isalnum()) for string in lst]

def make_lowercase(lst):
    return [string.lower() for string in lst]

def apply_preprocessing(lst):
    return make_lowercase(remove_special_char(lst.split()))

print(markdown("README.md"))