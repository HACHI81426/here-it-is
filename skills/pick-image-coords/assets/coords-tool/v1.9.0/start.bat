@echo off
chcp 65001 >nul
cd /d "%~dp0"
python pick_coords.py %*
pause
