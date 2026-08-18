@echo off
cd /d "%~dp0"
start "SUBIRU server" .venv\Scripts\python.exe -m subiru
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:5057/
