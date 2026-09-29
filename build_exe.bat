@echo off
setlocal
cd /d "%~dp0"
set PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
if exist "Zfav.ico" (
    "%PYTHON_EXE%" -m PyInstaller --onefile --noconsole --name APlusPracticeExam --icon=Zfav.ico --add-data "Zfav.ico;." app.py --collect-data data
) else (
    "%PYTHON_EXE%" -m PyInstaller --onefile --noconsole --name APlusPracticeExam app.py --collect-data data
)
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)
echo Build succeeded. Output is in the dist folder.
