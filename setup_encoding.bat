@echo off
echo Setting up Windows encoding for Python scripts...

REM Set UTF-8 encoding for the current session
chcp 65001 > nul

REM Set environment variables
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo UTF-8 encoding configured successfully!
echo You can now run your Python scripts with proper Unicode support.

pause
