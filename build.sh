#!/usr/bin/env bash
# Builds dist/AutoEvalBot — a fully standalone executable (Linux/macOS).
# End users need nothing installed except Google Chrome, which the bot drives.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .build-venv ]; then
    echo "Creating build environment..."
    python3 -m venv .build-venv
    ./.build-venv/bin/python -m pip install --quiet --upgrade pip
fi

echo "Installing dependencies..."
./.build-venv/bin/python -m pip install --quiet -r requirements.txt pyinstaller

echo "Building executable..."
./.build-venv/bin/pyinstaller --onefile --console --clean --noconfirm --name AutoEvalBot \
    --collect-all selenium --collect-submodules webdriver_manager auto_eval.py

if [ -f dist/AutoEvalBot ]; then
    chmod +x dist/AutoEvalBot
    echo
    echo "Done: dist/AutoEvalBot"
else
    echo
    echo "Build failed."
    exit 1
fi
