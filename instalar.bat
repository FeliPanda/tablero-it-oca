@echo off
title Instalador del Tablero IT OCA
cd /d "%~dp0"
echo.
echo === 1/4 Python ===
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" -3"
if not defined PY (
  echo Instalando Python 3.12 con winget...
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" (set "PY="%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" -3") else (set "PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"")
)
%PY% --version || (echo No se pudo instalar Python. Instalalo desde python.org y volve a ejecutar este archivo. & pause & exit /b 1)
echo.
echo === 2/4 Librerias ===
%PY% -m pip install --user --upgrade requests cryptography
echo.
echo === 3/4 Configuracion ===
if not exist publicar.env copy publicar.env.ejemplo publicar.env >nul
echo.
echo === 4/4 Tarea programada cada 30 minutos ===
schtasks /create /f /tn "Tablero IT OCA" /tr "\"%~dp0publicar.bat\"" /sc minute /mo 30
echo.
echo Listo. Se abre publicar.env: completa los tokens y la contrasena, guarda y cerra.
echo Despues ejecuta publicar.bat (doble clic) y revisa publicar.log.
start "" notepad publicar.env
pause
