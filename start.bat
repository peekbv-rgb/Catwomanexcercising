@echo off
setlocal
cd /d "%~dp0"
title Fitness Video Factory

echo ==============================================
echo   Fitness Video Factory 0.3.0 clean rebuild
echo ==============================================
echo.

set "PYTHON_CMD="
where py >nul 2>nul
if %errorlevel%==0 set "PYTHON_CMD=py -3.11"

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if %errorlevel%==0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo FOUT: Python is niet gevonden.
    echo Installeer Python 3.11 en vink "Add Python to PATH" aan.
    echo.
    pause
    exit /b 1
)

echo Python controleren...
%PYTHON_CMD% --version
if errorlevel 1 (
    echo.
    echo FOUT: Python kon niet worden gestart.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Virtuele omgeving maken...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo FOUT: .venv maken is mislukt.
        pause
        exit /b 1
    )
)

echo.
echo Pakketten installeren/controleren...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 (
    echo FOUT: pip upgrade is mislukt.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo FOUT: installatie van requirements is mislukt.
    echo Maak een screenshot van deze melding en stuur die door.
    pause
    exit /b 1
)

echo.
echo App starten op http://localhost:8501
echo Laat dit venster open zolang je de app gebruikt.
echo.
python -m streamlit run app.py

if errorlevel 1 (
    echo.
    echo De app is gestopt met een fout.
    pause
)

endlocal
