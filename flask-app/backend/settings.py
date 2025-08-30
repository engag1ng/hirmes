"""Utilities for reading and writing settings to config file.
"""

import json
import os

APP_FOLDER = os.path.join(os.getenv("APPDATA"), "Hirmes")
os.makedirs(APP_FOLDER, exist_ok=True)

SETTINGS_FILE = os.path.join(APP_FOLDER, "config.json")

def load_settings():
    """Loads settings from SETTINGS_FILE or creates it if it doesn't exist.

    Returns:
        dict: Settings with "name": value format.    
    """

    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding="utf-8") as f:
            return json.load(f)
    return {"recursive": False, "replace_filename": False, "watchdog_number": 50}

def save_settings(updates: dict):
    """Saves current settings to SETTINGS_FILE.

    Args:
        settings: In dictionary with "name": value format.
    """
    config = load_settings()

    config.update(updates)

    with open(SETTINGS_FILE, 'w', encoding="utf-8") as f:
        json.dump(config, f)