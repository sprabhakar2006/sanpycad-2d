#!/usr/bin/env python3
"""
app.py -- launches SanPyCAD 2D Sketch.

Starts the local geometry backend (backend/server.py, built on
ocad.py -- the same 2D functions SanPyCAD's own scripts use) and
opens it in its own application window using pywebview, so this
behaves like a normal desktop app. Falls back to your default browser
if pywebview isn't installed.

Run directly with:
    python3 app.py

For a native window (recommended):
    pip install pywebview
"""

import base64
import os
import sys
import socket
import threading
import time
import webbrowser

# Where backend/ and frontend/ live. Running from source that is simply
# this file's own folder. In a frozen (PyInstaller) build they are
# copied into the bundle's resource folder instead, which is not next
# to the executable -- see packaging/bundle_paths.py.
if getattr(sys, "frozen", False):
    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    sys.path.insert(0, os.path.join(BASE_DIR, "packaging"))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

import server  # noqa: E402

try:
    import bundle_paths  # noqa: E402  (frozen builds only)
except ImportError:
    bundle_paths = None


class Api:
    """
    Exposed to the frontend as `window.pywebview.api` (see `js_api=` below).
    Only reason this exists: "Save as PDF" used to build the PDF as a blob:
    URL and click a hidden <a download> link, which is the normal way to
    trigger a save in a real browser -- but pywebview's window is a native
    OS webview (WKWebView on macOS), not a browser with its own download
    manager. That webview just navigates itself to the blob: URL instead of
    saving anything, which is exactly what a user reported: the app's own
    page got replaced with no page to "go back" to, and no save location
    was ever shown because no real save ever happened. Routing the save
    through pywebview's own create_file_dialog()/plain file write instead
    gives a real native "Save As" dialog and an actual path to report back.
    """

    def save_pdf(self, filename, b64data):
        window = webview.windows[0]
        result = window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory=os.path.expanduser("~"),
            save_filename=filename or "sketch.pdf",
            file_types=("PDF Files (*.pdf)", "All files (*.*)"),
        )
        if not result:
            return None  # user cancelled
        # Different pywebview versions return either a bare path or a
        # 1-tuple/list containing it.
        path = result[0] if isinstance(result, (list, tuple)) else result
        if not path:
            return None
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64data))
        return path

    def save_sketch(self, filename, content):
        """
        Save a whole sketch (the JSON the frontend's own save/load format
        uses -- see saveSketchToText()/loadSketchFromText() in index.html)
        to a file the user picks via a real native Save dialog. `content`
        is plain text (JSON), not base64 -- unlike the PDF, which is
        binary, this is already just a string, so no encoding round-trip
        is needed to move it across the JS<->Python bridge.
        """
        window = webview.windows[0]
        result = window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory=os.path.expanduser("~"),
            save_filename=filename or "sketch.json",
            file_types=("Sketch files (*.json)", "All files (*.*)"),
        )
        if not result:
            return None  # user cancelled
        path = result[0] if isinstance(result, (list, tuple)) else result
        if not path:
            return None
        if not path.lower().endswith((".json", ".sketch")):
            path += ".json"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def open_sketch(self):
        """
        Native Open dialog for loading (or combining in) a previously
        saved sketch. Returns {"path": ..., "content": ...} or None if the
        user cancelled -- the frontend does the actual JSON parsing and
        entity merging (see the Open sketch / Combine sketch buttons).
        """
        window = webview.windows[0]
        result = window.create_file_dialog(
            webview.OPEN_DIALOG,
            directory=os.path.expanduser("~"),
            file_types=("Sketch files (*.json;*.sketch)", "All files (*.*)"),
        )
        if not result:
            return None
        path = result[0] if isinstance(result, (list, tuple)) else result
        if not path:
            return None
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"path": path, "content": content}

    def export_drawing(self, filename, content, ext):
        """
        Native Save dialog for DXF/SVG export -- same reasoning as
        save_sketch() above (pywebview's webview has no real download
        manager, so a real Save-As dialog + plain file write is used
        instead of a Blob/<a download> click). `ext` is 'dxf' or 'svg';
        `content` is plain text either way (both formats are text, unlike
        the PDF export's binary/base64 path).
        """
        window = webview.windows[0]
        ext = (ext or "dxf").lower().lstrip(".")
        label = "DXF" if ext == "dxf" else "SVG"
        result = window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory=os.path.expanduser("~"),
            save_filename=filename or f"sketch.{ext}",
            file_types=(f"{label} files (*.{ext})", "All files (*.*)"),
        )
        if not result:
            return None
        path = result[0] if isinstance(result, (list, tuple)) else result
        if not path:
            return None
        if not path.lower().endswith("." + ext):
            path += "." + ext
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def import_drawing(self):
        """
        Native Open dialog for importing a DXF or SVG drawing. Returns
        {"path": ..., "content": ..., "ext": "dxf"|"svg"} or None if the
        user cancelled -- the frontend picks /api/import_dxf vs
        /api/import_svg based on `ext` and feeds the result through the
        same mergeEntities() pipeline Combine-sketch already uses.
        """
        window = webview.windows[0]
        result = window.create_file_dialog(
            webview.OPEN_DIALOG,
            directory=os.path.expanduser("~"),
            file_types=("CAD drawings (*.dxf;*.svg)", "DXF files (*.dxf)", "SVG files (*.svg)", "All files (*.*)"),
        )
        if not result:
            return None
        path = result[0] if isinstance(result, (list, tuple)) else result
        if not path:
            return None
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"path": path, "content": content, "ext": ext}

    def copy_to_clipboard(self, text):
        """
        Writes `text` to the REAL system clipboard, from Python rather
        than the page's own JavaScript. The "Copy to clipboard" button
        (Export panel) used to call navigator.clipboard.writeText()
        directly -- that call resolves successfully and the button shows
        "Copied" even when nothing actually reached the OS clipboard,
        because pywebview's embedded webview has JS clipboard ACCESS
        disabled by default on several backends (macOS's WKWebView needs
        the private javaScriptCanAccessClipboard/DOMPasteAllowed
        preferences pywebview doesn't set; see
        https://github.com/r0x0r/pywebview/issues/1561) -- so the paste
        a user then tries elsewhere comes up with whatever was on the
        clipboard before, not the export code, and nothing in the UI
        ever indicated the write had silently failed.

        pyperclip (not tkinter) is used deliberately: this method runs on
        pywebview's own JS-bridge thread, not the main thread, and
        building a Tk() root off the main thread is unreliable-to-crashy
        on macOS's Cocoa. pyperclip instead shells out to each platform's
        own clipboard tool (pbcopy on macOS, a Win32 API call on Windows),
        neither of which cares which thread it's called from.

        Returns {"ok": True} on success or {"error": ...} if pyperclip
        isn't installed (or the platform copy tool it needs isn't
        available) -- the frontend falls back to the unreliable
        navigator.clipboard path in that case, since it's still better
        than nothing.
        """
        try:
            import pyperclip
            pyperclip.copy(text)
            return {"ok": True}
        except Exception as e:
            return {"error": str(e)}


def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_for_server(url, timeout=5.0):
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=0.5)
            return True
        except Exception:
            time.sleep(0.05)
    return False


def main():
    if bundle_paths is not None:
        bundle_paths.start_logging()
    server.print_backend_status()
    port = find_free_port()
    httpd, port = server.serve(host="127.0.0.1", port=port)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/"
    wait_for_server(url)
    print(f"[SanPyCAD 2D Sketch] backend running at {url}")

    try:
        global webview
        import webview
        webview.create_window(
            "SanPyCAD 2D Sketch", url, width=1200, height=800, min_size=(800, 560),
            # Explicitly off (this is also pywebview's documented default,
            # but some backends/versions have been flaky about honoring
            # that default -- see https://github.com/r0x0r/pywebview/issues/297).
            # Without this, a trackpad pinch or a stray ctrl+scroll signal
            # from a mouse can trigger the webview's own native page zoom,
            # which looks like "the whole app zoomed in and there's no way
            # back" and has nothing to do with this app's own pan/zoom
            # logic. The frontend also guards against this itself now
            # (see the gesturestart/gesturechange listeners in index.html).
            zoomable=False,
            # Exposes Api's methods to the page as window.pywebview.api.*
            # (see the Api class docstring -- this is what lets "Save as
            # PDF" use a real native Save dialog instead of the browser
            # download trick that doesn't work right in this webview).
            js_api=Api(),
        )
        # debug=True enables the native web inspector (right-click the
        # canvas -> Inspect Element), which is handy for seeing a real JS
        # stack trace instead of just the generic message in the app's own
        # status bar -- but on this setup it actually opens the inspector
        # panel automatically on every launch rather than just making it
        # available on demand, which is disruptive when you don't need it
        # (that Elements/Console panel docked under the window, closed by
        # hand every time). Left off by default; flip it back to True
        # temporarily if a future bug needs a real stack trace to
        # diagnose, then set it back to False afterward.
        webview.start(debug=False)
    except ImportError:
        print("[SanPyCAD 2D Sketch] pywebview not installed -- opening your "
              "default browser instead. For a real app window, run: "
              "pip install pywebview")
        webbrowser.open(url)
        print("[SanPyCAD 2D Sketch] press Ctrl+C here to stop the app")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    httpd.shutdown()


if __name__ == "__main__":
    main()
