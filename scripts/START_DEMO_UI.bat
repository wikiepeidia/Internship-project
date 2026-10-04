@echo off
REM Double-click launcher for the local browser web UI demo.
REM UIQ-03/D-02: this launches the browser demo, not the terminal analyzer.
cd /d "%~dp0.."
chcp 65001 >nul 2>&1

echo ============================================================
echo  VNPhish - Local Demo Web UI
echo  This opens a browser page with the chat-style demo.
echo  For a terminal-only, no-browser check, use
echo  START_TEXT_ANALYZE.bat instead.
echo ============================================================
echo.

python -m src.runtime.cli demo

echo.
echo Demo server stopped. Press any key to close this window.
pause >nul
