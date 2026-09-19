@echo off
REM Double-click to start the local demo in your browser.
REM
REM The Windows-level MODEL_* variables from the old D: drive setup make the app
REM refuse to start, so the three lines below replace them for this window only.
REM The model file is the local copy in data\runtime.
cd /d "%~dp0"
chcp 65001 >nul 2>&1

set "MODEL_STORAGE_ROOT=%CD%\data\runtime"
set "MODEL_ARTIFACT_ROOT=%CD%\data\runtime\models"
set "MODEL_REGISTRY_PATH=%CD%\data\runtime\manifests\model-registry.json"

echo ============================================================
echo  VNPhish - Local Demo
echo  Loading the model takes a few seconds. A browser tab opens
echo  by itself. One analysis takes about 30 seconds on CPU.
echo  Close this window to stop the demo.
echo ============================================================
echo.

python -m src.runtime.cli demo

echo.
echo Demo stopped. Press any key to close this window.
pause >nul
