#!/usr/bin/env python3
"""
build_bundle.py -- build the self-contained SanPyCAD-2D bundle for the
machine you run it on. One command, from the project root:

    python packaging/build_bundle.py

It produces dist/SanPyCAD-2D.app (macOS), dist/SanPyCAD-2D/ (Windows
and Linux), and a zip of that next to it, ready to attach to a GitHub
release. The result carries its own Python and every library, so the
person who downloads it installs nothing. The frontend is a single
self-contained index.html (no CodeMirror/Three.js vendor assets to
fetch, unlike SanPyCAD proper), so this is just PyInstaller + zip.

PyInstaller cannot cross-compile: a macOS bundle can only be built on
macOS and a Windows one only on Windows. Building both without owning
both machines is what .github/workflows/build-installers.yml is for --
it runs this same script on GitHub's macOS and Windows runners.
"""
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "packaging" / "sanpycad2d.spec"
DIST = ROOT / "dist"
BUILD = ROOT / "build"

IS_MAC = sys.platform == "darwin"
IS_WINDOWS = os.name == "nt"

# Imported by the app itself (not by this script) -- checked here so a
# missing one is reported now rather than as a broken bundle later.
RUNTIME_DEPS = ["numpy", "scipy", "sympy", "skimage", "webview", "pyperclip"]


def step(msg):
    print(f"\n==> {msg}", flush=True)


def check_deps():
    step("Checking build dependencies")
    if sys.version_info < (3, 10):
        print(f"  Python {sys.version.split()[0]} is too old -- SanPyCAD-2D needs 3.10+")
        sys.exit(1)
    print(f"  Python {sys.version.split()[0]}  ok")
    missing = []
    try:
        import PyInstaller  # noqa: F401
        print("  PyInstaller  ok")
    except ImportError:
        missing.append("pyinstaller")

    for name in RUNTIME_DEPS:
        try:
            __import__(name)
            print(f"  {name:12} ok")
        except ImportError:
            missing.append({"skimage": "scikit-image", "webview": "pywebview"}.get(name, name))

    if missing:
        print("\nMissing, and the bundle cannot be built without them:")
        print(f"    {sys.executable} -m pip install {' '.join(missing)}")
        sys.exit(1)


def run_pyinstaller():
    step("Running PyInstaller (this takes a few minutes)")
    for path in (BUILD, DIST):
        if path.exists():
            shutil.rmtree(path)
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(SPEC)]
    print(f"  {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, check=True)


def zip_result():
    step("Zipping the bundle")
    tag = "mac" if IS_MAC else ("win" if IS_WINDOWS else "linux")
    if IS_MAC:
        target, zip_path = DIST / "SanPyCAD-2D.app", DIST / f"SanPyCAD-2D-{tag}.zip"
        # ditto, not zipfile: it is the only thing that reliably keeps
        # the executable bit and symlinks inside a .app, without which
        # the unzipped app will not launch.
        subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                        str(target), str(zip_path)], check=True)
    else:
        target, zip_path = DIST / "SanPyCAD-2D", DIST / f"SanPyCAD-2D-{tag}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(target.rglob("*")):
                if path.is_file():
                    zf.write(path, Path("SanPyCAD-2D") / path.relative_to(target))

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  {zip_path.name}  ({size_mb:.0f} MB)")
    return target, zip_path


def main():
    check_deps()
    run_pyinstaller()
    target, zip_path = zip_result()
    print(f"\nBuilt: {target}")
    print(f"Ship:  {zip_path}")
    if IS_MAC:
        print("\nThis bundle is not notarized by Apple, so the first launch on "
              "another Mac shows an 'unidentified developer' warning: right-click "
              "the app > Open > Open. See README.md.")


if __name__ == "__main__":
    main()
