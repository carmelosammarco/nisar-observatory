#!/bin/sh
set -eu
cd "$(dirname "$0")"
export PYTHONPYCACHEPREFIX="$PWD/.pycache"
exec .venv/bin/python scripts/launch.py
