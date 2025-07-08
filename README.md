> **created by engag1ng**

<img src="https://github.com/user-attachments/assets/96a0beba-dc51-4a47-8a13-0f4801b08dbc" width="75%" height="75%">

A web-based IR sytem for indexing, searching and assigning ID's to files.

**⭐Please star this repository!**
## Getting started
This is a simple step-by-step guide on how to use this program.
### Prerequisites
- Python3 (tested on Python 3.13)
  - Visit https://www.python.org/downloads/ and download the latest version of Python3
> [!WARNING]
> Make sure to check `Add to PATH` when installing!
  
### Installation
1. Download the project files:

  - 1.1 Click the green *Code* button on top of the page and then click *Download Zip* (recommended)
  <img src="https://github.com/user-attachments/assets/1df8bd00-9800-4365-959a-e781238330fa" width="75%" height="75%">
  
  - 1.2 `git clone https://github.com/engag1ng/hirmes.git` (for advanced users)
2. Move the **ENTIRE** folder to your desired location
3. Open a command line in that folder. On Windows you can do so by right clicking into the folder and 'Open In Terminal'
4. Run the following commands:
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
``` 
### Usage
1. Execute the appropiate run script.

Windows: `run.bat`

2. Index files

2.1 Select the source folder that contains the files you would like to index.

2.2 Select your preferred settings using the checkboxes

2.3 Click **Index** and wait. The page will reload, when the indexing process is done.

3. Search files

3.1 Enter your search query. [Read more](#querying)

3.2 Click **Search**.

4. When you close the terminal, the web server closes and the service terminates. To restart the service simply return to Step 1.

## Documentation
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
(project AND management) OR project-management
```

This will first evaluate the expression in the paranthesis and then use it's result for further computation.

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

## License
This project is licensed under the MIT license! To learn more please visit https://opensource.org/license/mit 

## Contributing
If you have any recommendations, issues or improvements, please open an issue or pull request. Thank you!
