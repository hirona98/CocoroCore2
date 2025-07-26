@echo off
chcp 65001 > nul
echo CocoroCore2 Build Tool - MemOS Unified Backend

REM Python version check
python -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python 3.10 or higher is required
    echo Please install Python 3.10+ and try again
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    py -3.10 -m venv .venv
    if %errorlevel% neq 0 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call .\.venv\Scripts\activate

REM Check Python version in venv
python -c "import sys; print(f'Python {sys.version}')"

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies
    call deactivate
    pause
    exit /b 1
)

REM Execute build script
echo Running CocoroCore2 build script...
python build_cocoro2.py
set build_result=%errorlevel%

REM Deactivate virtual environment
call deactivate

if %build_result% neq 0 (
    echo.
    echo Build failed with error code %build_result%
    pause
    exit /b %build_result%
)

echo.
echo ========================================
echo CocoroCore2 build process completed successfully!
echo ========================================
echo.
echo Build output is in the 'dist' directory
echo.
pause