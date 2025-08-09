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
