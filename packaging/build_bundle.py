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


def patch_scipy():
    # scipy/stats/_distn_infrastructure.py ends a module-level cleanup
    # block with:
    #     for obj in [s for s in dir() if s.startswith('_doc_')]:
    #         exec('del ' + obj)
    #     del obj
    # The trailing "del obj" assumes the for-loop ran at least once and
    # left `obj` bound. Under PyInstaller's frozen import machinery the
    # list comprehension can come back empty at the point this file
    # executes, so `obj` is never bound and that last line raises
    # "NameError: name 'obj' is not defined" -- which happens inside
    # geom_ops.py's `from skimage.measure import ... approximate_polygon`
    # (skimage -> scipy.signal -> scipy.stats), so it kills the app
    # before any window ever opens, with no crash dialog. The for-loop
    # itself already deletes every matching name; the stray extra "del
    # obj" was only ever meant to tidy up the loop variable and is safe
    # to drop outright.
    step("Patching scipy (frozen-import NameError workaround)")
    try:
        import scipy.stats  # noqa: F401  -- just to locate the file below
        target = Path(scipy.stats._distn_infrastructure.__file__)
    except Exception as exc:
        print(f"  Could not locate scipy's _distn_infrastructure.py ({exc}) -- skipping")
        return

    text = target.read_text(encoding="utf-8")
    buggy = (
        "for obj in [s for s in dir() if s.startswith('_doc_')]:\n"
        "    exec('del ' + obj)\n"
        "del obj\n"
    )
    fixed = (
        "for obj in [s for s in dir() if s.startswith('_doc_')]:\n"
        "    exec('del ' + obj)\n"
    )
    if buggy not in text:
        if fixed in text:
            print(f"  {target.name}  already patched")
        else:
            print(f"  {target.name}  did not match the expected buggy text -- "
                  "scipy version differs; leaving it alone (may still crash)")
        return
    target.write_text(text.replace(buggy, fixed), encoding="utf-8")
    print(f"  {target.name}  patched")


def run_pyinstaller():
    step("Running PyInstaller (this takes a few minutes)")
    for path in (BUILD, DIST):
        if path.exists():
            shutil.rmtree(path)
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(SPEC)]
    print(f"  {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, check=True)


def sign_mac_app(target):
    # An entirely unsigned app is killed by macOS on launch on Apple
    # Silicon -- no window, no crash dialog, no log (it dies before the
    # app's own code, including bundle_paths.start_logging(), ever
    # runs). An ad-hoc signature (the "-" identity -- no Apple
    # Developer account needed) satisfies that check. This is not
    # notarization -- first launch still shows the "unidentified
    # developer" Gatekeeper warning, which the README explains how to
    # get past. CI does this same step itself after calling this
    # script, so this is a no-op to repeat there; it only matters for
    # bundles built locally via this script, which never otherwise get
    # signed at all.
    step("Ad-hoc signing the app (required on Apple Silicon)")
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(target)], check=True)


def zip_result():
    step("Zipping the bundle")
    tag = "mac" if IS_MAC else ("win" if IS_WINDOWS else "linux")
    if IS_MAC:
        target, zip_path = DIST / "SanPyCAD-2D.app", DIST / f"SanPyCAD-2D-{tag}.zip"
        sign_mac_app(target)
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
    patch_scipy()
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
