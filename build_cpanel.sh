#!/usr/bin/env bash
# Rebuild the cPanel bundle from the flask/ source of truth.
#
# Run this after ANY change under flask/. The cpanel/ folder is generated, not
# edited: anything changed there by hand is overwritten on the next run.
#
#   ./build_cpanel.sh            rebuild cpanel/ only
#   ./build_cpanel.sh --publish  rebuild, then copy into ~/Desktop/CPANEL/research-methods
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/flask"
DST="$HERE/cpanel"
PUBLISH_DIR="$HOME/Desktop/CPANEL/research-methods"

echo "==> rebuilding $DST from $SRC"
rm -rf "$DST"
mkdir -p "$DST"

# Application code, verbatim — one source of truth, no forked copies.
cp -r "$SRC"/. "$DST"/

# nginx serves the document root directly and ignores .htaccess, so the docroot
# is a separate folder holding nothing but public assets. Application source
# must never sit in it — that is how source code ends up downloadable.
mkdir -p "$DST/public"
if [ -d "$SRC/static" ]; then mkdir -p "$DST/public/static"; cp -r "$SRC/static/." "$DST/public/static/"; fi
cat > "$DST/public/.gitkeep" <<'EOF'
This folder is the subdomain's document root.

nginx serves whatever it finds here and ignores .htaccess. Only public assets
belong here — never application source, never .env, never data/.
EOF

# cPanel-specific files: Passenger entry point, requirements, env template,
# the hardening to append, and the deployment steps.
cp "$HERE/cpanel_extra/passenger_wsgi.py"   "$DST/"
cp "$HERE/cpanel_extra/requirements.txt"    "$DST/"
cp "$HERE/cpanel_extra/.env.example"        "$DST/"
cp "$HERE/cpanel_extra/htaccess.append.txt" "$DST/"
cp "$HERE/cpanel_extra/DEPLOY_STEPS.md"     "$DST/"
cp "$HERE/cpanel_extra/FILES_NOT_COPIED.md" "$DST/"

# Nothing that is not source or seed data may travel: no caches, no secrets,
# no test suites — tests belong in the repo, not in a 500 MB hosting quota.
find "$DST" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$DST" -name '*.pyc' -delete 2>/dev/null || true
rm -rf "$DST/tests" "$DST/.pytest_cache" 2>/dev/null || true
rm -f "$DST/.env" 2>/dev/null || true

echo "    $(find "$DST" -type f | wc -l) files, $(du -sh "$DST" | cut -f1)"

if [ "${1:-}" = "--publish" ]; then
  mkdir -p "$(dirname "$PUBLISH_DIR")"
  rm -rf "$PUBLISH_DIR"
  cp -r "$DST" "$PUBLISH_DIR"
  echo "==> published to $PUBLISH_DIR"
  echo "    now: ~/Desktop/CPANEL_PUSH.sh check research-methods"
fi
