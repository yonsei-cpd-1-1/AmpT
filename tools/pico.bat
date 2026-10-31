@echo off
rem Windows: .\tools\pico flash bench (same as tools/pico.sh on Mac)
if not exist "%~dp0..\.venv\Scripts\python.exe" (
  echo .venv is missing. Run: py -3 -m venv .venv
  exit /b 1
)
"%~dp0..\.venv\Scripts\python.exe" "%~dp0pico.py" %*
