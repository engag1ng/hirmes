#!/bin/bash
set -e
cd flask-app
pkill -f app 2>/dev/null || true
rm -f ../src-tauri/bin/app 2>/dev/null || true
source .venv/bin/activate
pyinstaller app.spec --distpath ../src-tauri/bin
deactivate
