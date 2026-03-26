@echo off
REM ─────────────────────────────────────────────────────────
REM  VEGO-AI Windows EXE builder
REM  Run this script on any Windows machine that has Python 3
REM ─────────────────────────────────────────────────────────

echo Installing build dependencies...
pip install pyinstaller pillow

echo.
echo Building VEGO-AI.exe...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "VEGO-AI" ^
  --add-data "multi_agent\extras\visualize_config.yaml;." ^
  multi_agent\extras\visualize_compliance.py

echo.
if exist dist\VEGO-AI.exe (
    echo SUCCESS! EXE is at: dist\VEGO-AI.exe
) else (
    echo BUILD FAILED. Check output above for errors.
)
pause
