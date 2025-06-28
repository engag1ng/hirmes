# automatic-id
> **created by engag1ng**

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
  
  - 1.2 `git clone https://github.com/engag1ng/automatic-id.git` (for advanced users)
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

Linux: `run.sh`

2. Index files
2.1 Select the source folder that contains the files you would like to index.
2.2 Select your preferred settings using the checkboxes
2.3 Click **Index** and wait. The page will reload, when the indexing process is done.

3. Search files
3.1 Enter your search query. [Read more](#querying)
3.2 Click **Search**.

4. When you close the terminal, the web server closes and the service terminates. To restart the service simply return to Step 1.

## Documentation
### Tokenizer
List of supported file types:
- PDF files
- Word documents (.DOCX)
- PowerPoint presentations (.PPTX)
- TXT files
- Markdown files (.MD)
### Querying
The querying engine supports different search operators to refine your search. A full list can be found below:

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
The OR operator can be used to express, that a file has to contain one of two search terms for it to be regarded.

Example query:
```
management OR geography
```

This will return all files that contain either *management* or *geography*.

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
