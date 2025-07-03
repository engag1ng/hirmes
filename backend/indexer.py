import dbm
import pickle
from pathlib import Path
from backend.tokenizer import pdf, docx, markdown, pptx, txt
import os
import datetime
from log import write_log

db_path = 'backend/index.db'
ignore_list = ["app.py", LOG_FILENAME, ".git", "backend", "LICENSE", "README.md", "requirements.txt", ".venv", ".gitignore"]

def index_files(paths):
    for path in paths:
        ext = Path(path).suffix.lower().lstrip(".")

        extractors = {
            "pdf": pdf,
            "txt": txt,
            "docx": docx,
            "doc": docx,
            "md": markdown,
            "pptx": pptx
        }

        if ext not in extractors:
            print(f"Unsupported file type: {ext}")
            return

        tokens = extractors[ext](path)

        with dbm.open(db_path, 'c') as db:
            for token in tokens:
                key = token[0].encode()

                if key in db:
                    postings = pickle.loads(db[key])
                    if path not in postings:
                        postings.append(path)
                        db[key] = pickle.dumps(sorted(postings))
                else:
                    db[key] = pickle.dumps([path])

def get_files_without_id(path, is_recursive):
    i = 0
    without_id = []
    
    entries = os.listdir(path)

    for entry in entries:
        full_path = os.path.join(path, entry)
        if entry not in ignore_list:
            if os.path.isdir(full_path) and is_recursive:
                additional_i, additional_without_id = get_files_without_id(full_path, is_recursive)
                i += additional_i
                without_id += additional_without_id
            elif os.path.isfile(full_path):
                if "★" not in entry:
                    without_id.append(full_path)
                    i += 1

    return i, without_id

def assign_id(is_replace_full, without_id):
    with_id = []
    for file in without_id:
        ID = datetime.datetime.now().strftime("%y%m%d%H%M%S.%f")
        dir_name = os.path.dirname(file)
        base_name = os.path.basename(file)
        file_name, file_extension = os.path.splitext(base_name)

        if is_replace_full:
            new_name = "★ " + ID + file_extension
        else:
            new_name = file_name + " ★ " + ID + file_extension

        new_path = os.path.join(dir_name, new_name)
        os.rename(file, new_path)
        with_id.append(new_path)

        write_log("0", ID, file, file_extension)
        
    return with_id
    
def check_file_status():
    with dbm.open(db_path, "c") as db:
        print("CODE NEEDED")