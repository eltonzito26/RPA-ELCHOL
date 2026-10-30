@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_EXE="
for %%V in (314 313 312) do (
  if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
  if not defined PYTHON_EXE if exist "%ProgramFiles%\Python%%V\python.exe" set "PYTHON_EXE=%ProgramFiles%\Python%%V\python.exe"
)
for %%V in (14 13 12) do (
  if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Python\pythoncore-3.%%V-64\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Python\pythoncore-3.%%V-64\python.exe"
)
if not defined PYTHON_EXE (
  echo No encontre Python 3.14, 3.13 ni 3.12.
  echo Tu Python 3.15 actual aun no tiene disponibles las dependencias OCR del proyecto.
  echo Instala Python 3.14 desde https://www.python.org/downloads/windows/ y vuelve a abrir este archivo.
  pause
  exit /b 1
)
echo Usando: %PYTHON_EXE%
"%PYTHON_EXE%" --version
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 goto failed
"%PYTHON_EXE%" -c "import pyclipper" >nul 2>&1
if errorlevel 1 (
  echo No se pudo cargar pyclipper, usado por el OCR.
  echo Instala el runtime Visual C++ 2015-2022 x64 desde PowerShell:
  echo winget install --id Microsoft.VCRedist.2015+.x64 --exact
  echo Despues vuelve a ejecutar este archivo.
  pause
  exit /b 1
)
echo Iniciando el recortador. Si se cierra, el error aparecera debajo y en recorte_run.log.
"%PYTHON_EXE%" -u recorte_tarjetas.py > recorte_run.log 2>&1
if errorlevel 1 (
  echo La aplicacion termino con error. Registro:
) else (
  echo La aplicacion se cerro. Registro:
)
if exist recorte_run.log type recorte_run.log
pause
exit /b 0
:failed
echo Fallo la instalacion de dependencias. La ventana quedara abierta para leer el mensaje.
pause
exit /b 1
