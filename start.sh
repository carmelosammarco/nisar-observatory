#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Project environment is missing. Run ./setup.sh first."
  exit 1
fi
.venv/bin/python -B scripts/stamp_assets.py
export PYTHONPYCACHEPREFIX="$PWD/.pycache"
exec .venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765 --no-access-log
