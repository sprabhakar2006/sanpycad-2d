"""
server.py -- loader stub. The real HTTP route table (the stdlib server
that the frontend canvas talks to) is shipped as encrypted source only,
under backend/_protected/server.enc -- see backend/_crypto_loader.py
for why and how, and build_protected_backend.py (in the main project
folder, not shipped here) for regenerating it after an edit.

Everything server.py has always exposed (serve(), print_backend_status(),
etc.) still works exactly the same via `import server` -- this stub just
hands the loading off transparently. In particular, __file__ is set to
THIS stub's own path before the real code runs, so its own
os.path.dirname(os.path.abspath(__file__))-based lookup of the
frontend/ folder still resolves correctly.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _crypto_loader import load_protected  # noqa: E402

load_protected(__name__, os.path.abspath(__file__))
