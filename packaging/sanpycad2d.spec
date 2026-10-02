# -*- mode: python ; coding: utf-8 -*-
"""
sanpycad2d.spec -- PyInstaller recipe for the self-contained
SanPyCAD-2D bundle: a CPython interpreter, every library the app
needs, and the app's own files in one folder the user can
double-click. Nothing has to be installed alongside it.

Build it with `python packaging/build_bundle.py` rather than invoking
pyinstaller by hand.

The one unusual thing here: backend/*.py (except __init__-style
plumbing) are NOT frozen as code. They are loader stubs that read
backend/_protected/<name>.enc from a path derived from their own
__file__, so they must stay real files on disk inside the bundle. They
are therefore shipped as DATA, and their module names are excluded so
PyInstaller's own frozen importer can't shadow the on-disk copies at
runtime. Because their real source is encrypted, PyInstaller cannot
scan it for imports either -- so everything those modules import is
listed by hand in hiddenimports below.
"""
import os
import sys

from PyInstaller.building.datastruct import Tree
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))
IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

# Backend modules shipped as encrypted source + on-disk loader stub.
# Keep in sync with build_protected_backend.py's MODULES list.
PROTECTED_MODULES = ["ocad", "server", "geom_ops", "cad_io"]
BACKEND_LOADED_FROM_DISK = PROTECTED_MODULES + ["_crypto_loader"]

# Same geometry stack as SanPyCAD/SanPyCAD-Brep: scipy.spatial
# (ConvexHull, cKDTree, Delaunay), scipy.interpolate (b-splines),
# skimage.measure/draw and sympy. skimage uses lazy_loader, so nothing
# is importable at analysis time -- whole packages are collected
# rather than named leaves. The image-I/O stack under skimage.io
# (OpenCV, Pillow, imageio, Qt) is excluded below: never reached, and
# would otherwise roughly triple the download.
hiddenimports = [
    "numpy", "sympy", "pyperclip", "webview",
    "scipy.spatial", "scipy.interpolate", "scipy.ndimage", "scipy.signal",
    "skimage.measure", "skimage.draw", "skimage._shared",
]
for pkg in ("scipy", "skimage", "sympy"):
    hiddenimports += collect_submodules(pkg)
hiddenimports += [
    "ast", "base64", "collections", "contextlib", "datetime", "functools",
    "http.server", "inspect", "io", "json", "math", "platform", "re",
    "shutil", "socket", "socketserver", "struct", "subprocess", "tempfile",
    "threading", "time", "traceback", "urllib.request", "warnings",
    "webbrowser", "xml.etree.ElementTree",
]

datas = collect_data_files("sympy")

a = Analysis(
    [os.path.join(PROJECT_ROOT, "app.py")],
    pathex=[PROJECT_ROOT, os.path.join(PROJECT_ROOT, "packaging")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=BACKEND_LOADED_FROM_DISK + [
        # open3d/cv2/Pillow/imageio/Qt/matplotlib/tkinter arrive as
        # incidental dependencies of scipy/skimage/sympy and are never
        # reached at runtime; cv2+Pillow+imageio+Qt alone are ~350 MB.
        "open3d", "cv2", "PIL", "imageio", "imageio_ffmpeg", "skimage.io",
        "PyQt5", "PyQt6", "PySide2", "PySide6", "matplotlib", "tkinter",
        "IPython", "jupyter", "notebook", "pytest", "pandas",
        "build123d", "OCP",
    ],
    noarchive=False,
)

# The app's own files, copied in as data (see the module docstring).
a.datas += Tree(os.path.join(PROJECT_ROOT, "backend"), prefix="backend",
                excludes=["__pycache__", "_protected_src", "*.pyc"])
a.datas += Tree(os.path.join(PROJECT_ROOT, "frontend"), prefix="frontend",
                excludes=["__pycache__", "*.pyc"])
a.datas += Tree(os.path.join(PROJECT_ROOT, "packaging"), prefix="packaging",
                excludes=["__pycache__", "*.pyc", "*.spec", "build_bundle.py",
                          "entitlements.plist"])

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SanPyCAD-2D",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # console=False everywhere: this is a windowed app, no terminal
    # pops up behind it on Windows.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=IS_MAC,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SanPyCAD-2D",
)

if IS_MAC:
    app = BUNDLE(
        coll,
        name="SanPyCAD-2D.app",
        icon=None,
        bundle_identifier="com.sanpycad.2d",
        info_plist={
            "CFBundleName": "SanPyCAD-2D",
            "CFBundleDisplayName": "SanPyCAD 2D Sketch",
            "CFBundleShortVersionString": os.environ.get("SANPYCAD2D_VERSION", "1.0.0"),
            "CFBundleVersion": os.environ.get("SANPYCAD2D_VERSION", "1.0.0"),
            "NSHighResolutionCapable": True,
            "LSBackgroundOnly": False,
            "NSRequiresAquaSystemAppearance": False,
        },
    )
