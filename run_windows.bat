@echo off
setlocal

cd /d "%~dp0"

if "%HOST%"=="" set "HOST=127.0.0.1"
if "%PORT%"=="" set "PORT=8000"

if defined PYTHON_EXE (
    set PYTHON_CMD="%PYTHON_EXE%"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3"
    ) else (
        where python >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_CMD=python"
        ) else (
            echo Python 3.11 or newer is required.
            echo Install Python from https://www.python.org/downloads/windows/ and enable "Add python.exe to PATH".
            pause
            exit /b 1
        )
    )
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
    echo Python 3.11 or newer is required.
    echo Run the installer again or install Python from https://www.python.org/downloads/windows/.
    pause
    exit /b 1
)

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
    if errorlevel 1 (
        echo The existing virtual environment uses Python older than 3.11.
        echo Rename or remove the venv folder manually, then run this launcher again.
        pause
        exit /b 1
    )
)

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv venv
    if errorlevel 1 (
        echo Could not create the virtual environment.
        pause
        exit /b 1
    )
)

echo Installing Python dependencies...
"venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Could not upgrade pip.
    pause
    exit /b 1
)

"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Could not install dependencies.
    pause
    exit /b 1
)

if not exist "studio.db" (
    echo Creating demo workspace...
    "venv\Scripts\python.exe" scripts\seed_demo.py
    if errorlevel 1 (
        echo Could not create the demo workspace.
        pause
        exit /b 1
    )
)

echo Starting FramersHaven at http://%HOST%:%PORT%
echo Press Ctrl-C in this window to stop the app.
start "" powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:%PORT%'"
"venv\Scripts\python.exe" -m uvicorn app.main:app --host %HOST% --port %PORT%

endlocal
