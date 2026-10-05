@echo off
title DigitalGuard - Digital Addiction Predictor
echo.
echo ==========================================
echo     DigitalGuard ML Risk Predictor
echo ==========================================
echo.
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -m venv .venv
)
call .venv\Scripts\activate.bat
echo Installing/updating dependencies...
python -m pip install -r requirements.txt
echo.
echo Starting application...
python app.py
pause
