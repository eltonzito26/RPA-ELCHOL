@echo off
setlocal
py -3 -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 pause
