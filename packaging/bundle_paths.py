"""
bundle_paths.py -- path plumbing used ONLY by the frozen (PyInstaller)
build of SanPyCAD 2D Sketch. Running from source never imports this file.

What changes when the app is frozen into a bundle: where the app's own
files live. From source, app.py sits next to backend/ and frontend/.
Inside a bundle those are copied into PyInstaller's resource directory
(sys._MEIPASS: Contents/Frameworks on macOS, _internal\\ on Windows),
which is somewhere else entirely and is NOT next to the executable the
user clicked -- see resource_dir() below, used by app.py's BASE_DIR.

This app has no config file and no imports/ folder to redirect (unlike
SanPyCAD proper) -- the only other thing it writes is its own log, via
start_logging() below, which goes to the per-user application data
folder since a bundle in /Applications or Program Files is read-only:

    macOS    ~/Library/Application Support/SanPyCAD-2D
    Windows  %APPDATA%\\SanPyCAD-2D
    Linux    ~/.local/share/SanPyCAD-2D  (XDG_DATA_HOME if set)
"""
import os
import sys

APP_NAME = "SanPyCAD-2D"


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def resource_dir():
    """The folder that backend/ and frontend/ sit in."""
    if is_frozen():
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def user_data_dir():
    """Per-user, always-writable folder for this app's own data."""
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def start_logging():
    """Send the app's console output to a log file.

    A windowed bundle has no terminal attached, so everything the app
    prints would otherwise be lost. PyInstaller replaces
    sys.stdout/sys.stderr with a null writer in windowed mode, so
    without this there is no way at all to see what went wrong on a
    user's machine. The file is truncated on each launch, so it always
    describes the current session rather than growing forever.

    Returns the log path, or None when not frozen (running from source
    already has a terminal).
    """
    if not is_frozen():
        return None
    log_path = os.path.join(user_data_dir(), "SanPyCAD-2D.log")
    try:
        stream = open(log_path, "w", encoding="utf-8", buffering=1)
    except OSError:
        return None
    sys.stdout = stream
    sys.stderr = stream
    return log_path
