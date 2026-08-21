@echo off
rem Builds dist\AutoEvalBot.exe — a fully standalone executable.
rem End users need nothing installed (only Chrome, which the bot drives).

cd /d "%~dp0"

if not exist .build-venv (
    echo Creating build environment...
    python -m venv .build-venv
    .\.build-venv\Scripts\python.exe -m pip install --quiet --upgrade pip
)

echo Installing dependencies...
.\.build-venv\Scripts\python.exe -m pip install --quiet requests selenium webdriver-manager pyinstaller

echo Building exe...
.\.build-venv\Scripts\pyinstaller.exe --onefile --console --clean --name AutoEvalBot ^
    --collect-all selenium --collect-submodules webdriver_manager auto_eval.py

if exist dist\AutoEvalBot.exe (
    echo.
    echo Done: dist\AutoEvalBot.exe
) else (
    echo.
    echo Build failed.
    exit /b 1
)
