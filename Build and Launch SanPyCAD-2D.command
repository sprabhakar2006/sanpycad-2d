#!/bin/bash
# One-click: builds the self-contained SanPyCAD-2D.app bundle on this
# Mac and launches it. Safe to re-run any time you want a fresh build
# (e.g. after pulling new source) -- it always rebuilds from scratch.
set -uo pipefail
cd "$(dirname "$0")"

echo "=== SanPyCAD-2D: build and launch ==="
echo

# Close any already-running copy first, so the new build isn't fighting
# a stale instance still holding the port / files open.
pkill -f "dist/SanPyCAD-2D.app/Contents/MacOS/SanPyCAD-2D" 2>/dev/null || true

PYTHON_BIN="python3"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3.10+ from python.org and re-run this."
  read -p "Press Enter to close..."
  exit 1
fi

VENV_DIR=".build_venv"
if [ ! -d "$VENV_DIR" ]; then
  echo "Setting up a private build environment (first run only)..."
  "$PYTHON_BIN" -m venv "$VENV_DIR" || { echo "Failed to create venv."; read -p "Press Enter to close..."; exit 1; }
fi

source "$VENV_DIR/bin/activate"

echo "Installing/updating build dependencies..."
pip install --quiet --upgrade pip
pip install --quiet numpy scipy sympy scikit-image pywebview pyperclip pyinstaller \
  || { echo; echo "!!! Dependency install failed -- see the error above."; read -p "Press Enter to close..."; exit 1; }

echo
echo "Building the app (this can take a few minutes)..."
rm -rf dist build
python packaging/build_bundle.py || { echo; echo "!!! Build failed -- see the error above."; read -p "Press Enter to close..."; exit 1; }

deactivate

echo
echo "Build complete. Launching SanPyCAD-2D..."
open "dist/SanPyCAD-2D.app"

echo
echo "Done! SanPyCAD-2D should now be opening in its own window."
echo "The built app lives at: dist/SanPyCAD-2D.app"
echo "A zip ready to share is at: dist/SanPyCAD-2D-mac.zip"
read -p "Press Enter to close..."
