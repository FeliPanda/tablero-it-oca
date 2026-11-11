@echo off
cd /d "%~dp0"
python publicar.py >> publicar.log 2>&1
