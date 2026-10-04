@echo off
REM Double-click launcher for the terminal text-only analyzer.
REM UIQ-03/D-02: this is text-only and opens no browser page.
REM Do not read pasted text into a variable; python -m src.runtime.cli analyze
REM reads stdin directly.
cd /d "%~dp0.."
chcp 65001 >nul 2>&1

echo ============================================================
echo  VNPhish - Terminal Text Analyzer (text-only, no browser)
echo  Paste the suspicious message below, then press Ctrl+Z
echo  followed by Enter to finish and analyze it.
echo  For the browser demo UI instead, use START_DEMO_UI.bat.
echo ============================================================
echo.

python -m src.runtime.cli analyze

echo.
echo Analysis finished. Press any key to close this window.
pause >nul
