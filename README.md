# Hirmes
> **created by engag1ng**

<img width="75%" alt="image" src="https://github.com/user-attachments/assets/c023c8f4-7f45-45a6-8a12-a6bdf3fd2a35" />

A local IR sytem for indexing, searching and assigning ID's to files.
Powered by:

<div align="center">
	<code><img width="50" src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/python/python-original.svg" alt="Python" title="Python"/></code>
	<code><img width="50" src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/flask/flask-original.svg" alt="Flask" title="Flask"/></code>
	<code><img width="50" src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/javascript/javascript-original.svg" alt="JavaScript" title="JavaScript"/></code>
	<code><img width="50" src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/tauri/tauri-original-wordmark.svg" alt="Rust" title="Rust"/></code>
	<code><img width="50" src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/npm/npm-original-wordmark.svg" alt="npm" title="npm"/></code>
</div>

**⭐Please star this repository!**
## Getting started
This is a simple step-by-step guide on how to use this program.

### Prerequisites
- Python3 (tested on Python 3.13)
  - Visit https://www.python.org/downloads/ and download the latest version of Python3
> [!WARNING]
> Make sure to check `Add to PATH` when installing!
  
### Installation
1. Clone the project files:

```cmd
git clone https://github.com/engag1ng/hirmes.git
```
2. Open a command line in the project root.
3. Run the following commands:

```cmd
cd flask-app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
``` 

### Build
In `/`
```cmd
npm run tauri build
```

Result can be found in `src-tauri/target/release/`.

### Usage
1. Execute `hirmes.exe`.
2. Select the source folder that contains the files you would like to index.
3. Select your preferred settings using the checkboxes
4. Click **Index** and wait. A message will be displayed, when the indexing process is done.
5. Enter your search query and click **Search**. [Read more](#querying)

### Indexing
List of supported file types:
- PDF files \*
- Word documents (.DOCX)
- PowerPoint presentations (.PPTX) \*
- TXT files
- Markdown files (.MD)

\* Supports page-by-page indexing

### Querying
The querying engine supports different search operators to refine your search. 

It is **necessary** to use operators when evaluating multiple search terms. For example "project management" will raise an error. Instead use either "project AND management" or "project OR management". This removes ambiguity, makes searches faster and more precise. To learn more about the search operators read the section below.

Search results are ranked in the following order:
1. Number of matching terms
2. Sum of term frequencies for all matching terms

**Paranthesis ()**:
Paranthesis can be used to execute a certain portion of the query first and then further evaluate it later. Those familiar with algebra will recognise this from mathematic equations.

Example query:
```
( project AND management ) OR project-management
```

This will first evaluate the expression in the paranthesis and then use it's result for further computation.

!!!

Note that paranthesis should be placed seperate from words to be recognized as individual operators instead of parts of a word.

**AND Operator**:
The AND operator can be used to express, that a file has to contain both search terms for it to be regarded.

Example query:
```
project AND management
```

This will only return files that contain the words *project* and *management*.

**OR Operator**:
The OR operator returns all files, that contain one or the other search word.

Example query:
```
management OR geography
```

This will return all files containing either *management* or *geography*.

**NOT Operator**:
The NOT operator disregards all files, that contain a certain search term.

Example query:
```
management NOT geography
```

This will return all files that contain *management* but not *geography*.

## Documentation

- Always run `pylint` and `pytest` on your code before pushing.
- It is recommended to use type hints and run `pytype` before pushing.

### Style guide
- Boolean variables must be denoted by the prefix `is`.
- Every module should be started by docstring expaining it's usage.
	- Needs to start with a one line summary
	- Followed by a more extensive explanation
- Functions and methods need to be docstringed.
	- Needs to start with a one line summary
	- If necessary followed by a more extensive explanation
	- Needs to contain sections: Args, Returns (or Yields), Raises
- Classes need to be docstringed.
	- Needs to start with a one line summary
	- If necessary followed by a more extensive explanation
	- Needs to contain Attributes section
- Lists / arrays should only be used when all elements are the same type, in other cases use tuples.
- Prefer tuples for function returns

#### Python
- Naming: ClassName, local_var_name, GLOBAL_CONSTANT_NAME (follow snake case)
#### JavaScript
- Naming: packageName, ClassName, CONSTANT_NAME, variableName


## License
This project is licensed under a custom license! Please read the LICENSE file. 

## Contributing
If you have any recommendations, issues or improvements, please open an issue or pull request. Thank you!
