@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Fitness Video Factory

echo ========================================
echo   Fitness Video Factory - Windows start
echo ========================================
echo.

REM Find a usable Python installation.
set "PYTHON_CMD="
py -3.11 --version >nul 2>&1 && set "PYTHON_CMD=py -3.11"
if not defined PYTHON_CMD py --version >nul 2>&1 && set "PYTHON_CMD=py"
if not defined PYTHON_CMD python --version >nul 2>&1 && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  echo [FOUT] Python is niet gevonden op deze pc.
  echo Installeer Python 3.11 of 3.12 vanaf https://www.python.org/downloads/
  echo Vink tijdens installatie "Add Python to PATH" aan.
  echo.
  pause
  exit /b 1
)

echo Python gevonden:
%PYTHON_CMD% --version
echo.

if not exist ".env" (
  echo [FOUT] Bestand .env ontbreekt.
  echo Maak een kopie van .env.example, noem deze .env en zet daarin je Runway API-key.
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Virtuele Python-omgeving wordt aangemaakt...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error

echo Benodigde pakketten worden gecontroleerd/geinstalleerd...
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo.
echo App wordt gestart. Je browser opent op http://localhost:8501
echo Sluit dit zwarte venster NIET zolang je de app gebruikt.
echo.
python -m streamlit run app.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo ========================================
echo [FOUT] Het starten is mislukt.
echo Maak een screenshot van de fout hierboven en stuur die naar ChatGPT.
echo ========================================
echo.
pause
exit /b 1
