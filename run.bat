@echo off
echo Starting CocoroCore2 in development mode...
echo.

REM Activate virtual environment
call .\.venv\Scripts\activate

REM Run CocoroCore2 as module
python -X utf8 -m src.main

REM Deactivate on exit
call deactivate

pause