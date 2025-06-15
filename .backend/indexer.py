import dbm
import pickle
from pathlib import Path
from tokenizer import pdf, docx, markdown, pptx, txt

db_path = '.backend/index.db'

dbm.open(db_path, 'c')

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