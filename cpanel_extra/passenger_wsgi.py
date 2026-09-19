"""Passenger WSGI entry point — cPanel / CloudLinux Python Selector.

Application : research-methods
Subdomain   : https://research-methods.harold-datascience.co.ke
App root    : apps/research-methods
Document root: apps/research-methods/public      <- separate, holds no source
Target      : Python 3.11
Resolution  : create_app() factory

cPanel's "Setup Python App" imports this file and looks for a module-level
callable named `application`. It must never start a development server —
Passenger owns the listening socket.

The app module is imported normally, never as "__main__", so any
`if __name__ == "__main__": app.run(...)` block is skipped. Flask.run is also
replaced with a no-op as belt and braces.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE / "src"):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
os.chdir(str(HERE))

_envf = HERE / ".env"
if _envf.is_file():
    for _line in _envf.read_text(errors="replace").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

os.environ.setdefault("FLASK_ENV", "production")
os.environ.setdefault("FLASK_DEBUG", "0")
os.environ.setdefault("SITE_DOMAIN", "research-methods.harold-datascience.co.ke")
os.environ.setdefault("SITE_SCHEME", "https")
os.environ.setdefault("SITE_NAME", "Research Methods")

import flask  # noqa: E402

flask.Flask.run = lambda self, *a, **k: None  # Passenger serves; never self-serve.

import importlib  # noqa: E402

_module = importlib.import_module("app")

# Passenger looks up this exact name. Resolved off the imported module rather
# than assumed to be in this file's namespace — `application = app` names
# nothing here, which is a NameError at import and a 500 with no page.
application = _module.create_app()

if __name__ == "__main__":
    print("WSGI callable resolved:", application)
