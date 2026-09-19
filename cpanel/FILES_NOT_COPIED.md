# What this bundle deliberately leaves out

`build_cpanel.sh` regenerates this folder from `flask/`. These are excluded on
purpose:

| Left out | Why |
|---|---|
| `tests/` | The repository keeps them. A 500 MB hosting quota should not. |
| `__pycache__/`, `*.pyc` | Rebuilt on the server, and they bloat the upload. |
| `.env` | Secrets belong in cPanel's environment-variable panel, never in a file under the document root. |
| `.git/` | Not needed to serve. |

Anything under `public/` is the subdomain's document root and is world-readable
by design. Nothing else in this folder should ever be moved into it.
