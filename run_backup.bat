@echo off
title Amazon Backup Sync - Local Runner
color 0A

echo.
echo =====================================
echo   AMAZON BACKUP SYNC - LOCAL RUNNER
echo =====================================
echo.
echo Fetching last 2 days of Amazon orders...
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH
    echo Please install Python or add it to your PATH
    pause
    exit /b 1
)

REM Check if credentials file exists
if not exist "google_credentials.json" (
    echo ERROR: google_credentials.json not found
    echo Please place your Google service account credentials in this folder
    pause
    exit /b 1
)

REM Check if backup script exists
if not exist "backup_column_file_fixed.py" (
    echo ERROR: backup_column_file_fixed.py not found
    echo Please ensure the backup script is in this folder
    pause
    exit /b 1
)

echo Starting backup process...
echo.

REM Run the backup script
python backup_column_file_fixed.py

echo.
echo =====================================
echo Backup process completed!
echo Check your Google Sheet for results.
echo =====================================
echo.
pause
