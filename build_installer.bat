@echo off
setlocal
cd /d "%~dp0"

if not exist "dist\APlusPracticeExam.exe" (
    echo ERROR: dist\APlusPracticeExam.exe was not found.
    echo Build the app first with: build_exe.bat
    exit /b 1
)

where iscc >nul 2>nul
if errorlevel 1 (
    echo ERROR: Inno Setup is not installed or is not on PATH.
    echo Download it from: https://jrsoftware.org/isinfo.php
    exit /b 1
)

iscc installer.iss
if errorlevel 1 (
    echo Installer build failed.
    exit /b 1
)

echo Installer build succeeded. Output is in the Output folder.
