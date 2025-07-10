cd flask-app
taskkill /f /im app.exe >nul 2>&1
del ..\src-tauri\bin\app.exe >nul 2>&1
call .venv\Scripts\activate
pyinstaller app.spec --distpath ..\src-tauri\bin
deactivate
