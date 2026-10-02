"""
cad_io.py -- loader stub. The real DXF/SVG import+export module is
shipped as encrypted source only, under backend/_protected/cad_io.enc
-- see backend/_crypto_loader.py for why and how, and
build_protected_backend.py (in the main project folder, not shipped
here) for regenerating it after an edit.

Everything cad_io.py has always exposed (export_dxf, import_dxf,
export_svg, import_svg, etc.) still works exactly the same via
`import cad_io` -- this stub just hands the loading off transparently.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _crypto_loader import load_protected  # noqa: E402

load_protected(__name__, os.path.abspath(__file__))
