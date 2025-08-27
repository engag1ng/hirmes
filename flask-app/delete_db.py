"""Deletes database file for a fresh start.
"""

import os

APP_FOLDER = os.path.join(os.getenv("APPDATA"), "Hirmes")
os.makedirs(APP_FOLDER, exist_ok=True)

DB_PATH = os.path.join(APP_FOLDER, "index.db")

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    print("File doesn't exist!")
