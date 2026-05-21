# 0.4.0 (2026-05-20)
## Added
* Linux compatibility
* Various tests and benchmarks
## Changed
* Progress bar now portrays actual indexing progress
* Speed up indexing and AND/OR evaluation by 50%
## Removed
## Fixed
* _get_files_without_id would never close connection
* database access would fail due to blocking

# 0.3.0 (2025-10-02)
## Added
* Settings menu
* Option to change watchdog listener list
* Option to change watchdog reindexing number
* Option to select enabled extensions
* Document hyperlink in search results
* Tagging extension
* Program added to auto-start
* Quick open shortcut (CTRL+Shift+Space)
## Changed
* Watchdog removes missing documents on search
## Removed
* File rename when indexing


# 0.2.0 (2025-09-05)
## Added
* Watchdog that automatically finds, removes and reindexes files
* Extra confirm popup for destructive features
* Full text search checkbutton
* Indexing progress bar
## Changed
* Search tests are more refined

# 0.1.2 (2025-08-27)
## Added
* "Did You Mean" spellchecking recommendation
* Database deletion script
* Style and code guidelines
* Documentation for functions and modules
* Pylint for testing
## Changed
* Optimised database structure
* Optimised stoplist access
## Fixed
* Window sizes too small
* Paranthesis not working in queries
* Searching and indexing failing randomly
* RPN structure not correct
* Underscores would cause error in search
* Fixed spellchecking time

# 0.1.1 (2025-08-09)
## Added
* Splashscreen
* Tests for Indexer
## Changed
* Improved indexing times by 750%
## Fixed
* RPN would always fail
* app.exe wouldn't correctly close
* ID was assigned even when file was not indexed

# 0.1.0-beta.2 (2025-07-20)
## Added
* Security clean-up script
* Pytest for spellcheck
## Changed
* Spellcheck now via symspellpy
* Program files moved to "AppData/Roaming/Hirmes"
* Ajax instead of page reload when searching or indexing
## Removed
* Custom dictionary

# 0.1.0-beta (2025-07-14)
## Added
* Query spellcheck using levenshtein distance
* Search result ranking
* Context window (snippet) for results
## Changed
* PDF's and PowerPoint's are now indexed page-by-page
* UI now via Tauri
## Removed
* Log file (log.csv)
## Fixed
* Error handling significantly improved

# 0.1.0-alpha (2025-06-28)
## Added
* Indexer allowing users to index files in database
* Search engine allowing users to search index
* Local Webview using Flask
* Dark/Light mode options
* Config, that remembers last selected options
## Changed
* Original python script replaced with OS dependent run script.
