@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
echo Running from: %~dp0src
python -m talabat_wallet
pause
