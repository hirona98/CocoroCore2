@echo off
echo Starting CocoroCore2 in development mode...
echo.

REM Activate virtual environment
call .\.venv\Scripts\activate

REM Run CocoroCore2 as module
python -m src.main --environment development

REM Deactivate on exit
call deactivate

pause