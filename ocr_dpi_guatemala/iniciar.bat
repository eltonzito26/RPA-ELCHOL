@echo off
setlocal
if exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" set "PATH=%PATH%;%ProgramFiles%\Tesseract-OCR"
if exist "%ProgramFiles(x86)%\Tesseract-OCR\tesseract.exe" set "PATH=%PATH%;%ProgramFiles(x86)%\Tesseract-OCR"
py -3 "%~dp0ocr_dpi.py" %*
if errorlevel 1 pause
