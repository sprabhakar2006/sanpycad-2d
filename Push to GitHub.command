#!/bin/bash
# One-time: pushes this folder's code to github.com/sprabhakar2006/sanpycad-2d,
# then tags v1.0.0 to trigger the automated build (mac-arm64/mac-intel/win-x64
# zips attached to a GitHub Release). The first push will ask you to log into
# GitHub in a browser window or popup -- that's normal, go ahead and sign in.
set -uo pipefail
cd "$(dirname "$0")"

echo "=== Pushing SanPyCAD-2D to GitHub ==="
echo

git branch -M main
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/sprabhakar2006/sanpycad-2d.git

echo "Pushing code..."
git push -u origin main || { echo; echo "!!! Push failed -- see the error above."; read -p "Press Enter to close..."; exit 1; }

echo
echo "Tagging v1.0.0 to trigger the automated build..."
git tag -f v1.0.0
git push --force origin v1.0.0 || { echo; echo "!!! Tag push failed -- see the error above."; read -p "Press Enter to close..."; exit 1; }

echo
echo "All done! Check the build progress at:"
echo "  https://github.com/sprabhakar2006/sanpycad-2d/actions"
echo "When it finishes, the zips appear at:"
echo "  https://github.com/sprabhakar2006/sanpycad-2d/releases"
read -p "Press Enter to close..."
