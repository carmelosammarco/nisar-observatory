#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  if [ -n "${NISAR_PYTHON:-}" ]; then
    "$NISAR_PYTHON" -m venv .venv
  elif command -v python3.12 >/dev/null 2>&1; then
    python3.12 -m venv .venv
  else
    echo "Set NISAR_PYTHON to a Python 3.12+ executable, then run setup.sh."
    exit 1
  fi
fi
.venv/bin/python -c 'import sys; assert sys.version_info >= (3,12), "Python 3.12+ is required"'
.venv/bin/python -m pip install -r requirements-lock.txt
