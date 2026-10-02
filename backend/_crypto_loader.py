"""
_crypto_loader.py -- shared helper used by the tiny stub files
(ocad.py, geom_ops.py, cad_io.py, server.py) that sit in this backend/
folder. This file itself has nothing to hide (it's just import
plumbing), which is exactly why it's the one thing here left as plain,
readable source.

Why this exists: the 4 modules above contain the actual app logic (the
geometry engine, the AutoCAD-style editing ops, the DXF/SVG reader/
writer, and the HTTP route table), which this app ships as encrypted
source only -- backend/_protected/<name>.enc -- rather than as plain
.py text, so a curious end user opening the folder doesn't find
readable Python they can just copy out. Each stub file below is a few
lines that hand off to load_protected() here, which decrypts the
matching .enc file and runs it in the stub's own module slot, so
callers see no difference at all: `import ocad as o4` still gives you
every function ocad.py always had.

HOW THIS DIFFERS FROM (AND FIXES) THE EARLIER BYTECODE-BASED ATTEMPT:
That version compiled the real source down to .pyc bytecode, which is
tied to an exact CPython minor version (a 3.10 build won't load under
3.11, 3.12, etc) -- and broke on a Windows machine that wasn't running
the one Python version available to compile against. This version
instead encrypts the SOURCE TEXT itself. Decrypting it just gets back
the original .py text, which is then handed to Python's own compile()
+ exec() -- exactly what the interpreter does for every normal .py
file on disk, regardless of Python version. There is no
version-specific format anywhere in this scheme, so it runs on any
CPython 3.x the same way the plain .py files always did.

HONEST LIMITS -- read this before assuming it's "secure": the key
below has to ship inside the app itself, since nothing here ever asks
the end user for a password ("only give access internally to the
software" was the ask). That means anyone willing to open this file
and read _KEY_HEX can decrypt the .enc files themselves -- this is
true of every purely client-side, no-password, no-server-check
protection scheme, not a flaw specific to this implementation (it's
the same fundamental limit commercial DRM/obfuscation tools run into).
What this DOES achieve: a end user browsing the installed app's files
in a text editor or archive tool sees no readable Python at all, which
stops casual/accidental exposure -- the realistic threat model for
"don't let a customer just read my source," as opposed to defending
against someone deliberately reverse-engineering the app.

The cipher: a XOR stream generated from repeated SHA-256 hashing of
(key + block counter) -- stdlib-only (hashlib), no third-party crypto
dependency to keep this app's "stdlib only" philosophy (see server.py's
own docstring) and to avoid adding yet another package the end user's
Python would need. It is NOT a standards-vetted cipher (not AES-GCM or
similar) -- it's a lightweight, adequate-for-this-purpose deterrent,
not something to rely on for defending genuinely sensitive data.
"""
import hashlib
import importlib.util
import os
import sys

# Embedded key -- see the module docstring's "HONEST LIMITS" section.
# Regenerate with `python3 -c "import secrets; print(secrets.token_hex(32))"`
# and re-run build_protected_backend.py if you ever want to rotate it.
_KEY_HEX = "005de1582154733e6573deaa06fc6e1497de3384af6546f6ee970e55daa1ff85"
_KEY = bytes.fromhex(_KEY_HEX)


def _keystream(length):
    out = bytearray()
    counter = 0
    while len(out) < length:
        out += hashlib.sha256(_KEY + counter.to_bytes(8, "big")).digest()
        counter += 1
    return bytes(out[:length])


def _xor(data):
    """Symmetric -- the same function encrypts and decrypts."""
    ks = _keystream(len(data))
    return bytes(a ^ b for a, b in zip(data, ks))


def encrypt_source(source_text):
    """str (Python source) -> encrypted bytes, for the build script."""
    return _xor(source_text.encode("utf-8"))


def decrypt_source(blob):
    """encrypted bytes -> str (Python source)."""
    return _xor(blob).decode("utf-8")


def load_protected(modname, stub_path):
    """
    Decrypts modname's real source from backend/_protected/<modname>.enc
    and runs it as if it were the code of the stub sitting at
    `stub_path` (i.e. backend/<modname>.py's own location) -- so any
    __file__-relative logic inside the real module (server.py locating
    frontend/index.html, for instance) keeps resolving exactly as it
    would if the real source were sitting right there in backend/.

    `modname` must already be registered in sys.modules (true for any
    module mid-import, which is the only time a stub ever calls this).
    """
    backend_dir = os.path.dirname(os.path.abspath(stub_path))
    enc_path = os.path.join(backend_dir, "_protected", modname + ".enc")

    if not os.path.isfile(enc_path):
        raise ImportError(
            f"Missing encrypted module file for '{modname}': {enc_path}. "
            f"This copy of the app is incomplete -- backend/_protected/ "
            f"should contain a .enc file for every stub in backend/."
        )

    with open(enc_path, "rb") as f:
        source = decrypt_source(f.read())

    module = sys.modules[modname]
    module.__file__ = stub_path
    module.__spec__ = importlib.util.spec_from_loader(modname, loader=None, origin=stub_path)
    code = compile(source, stub_path, "exec")
    exec(code, module.__dict__)
    return module
