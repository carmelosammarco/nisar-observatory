"""Keep all test-module imports away from the owner's ordinary runtime.

This must execute before backend.access is imported during test collection.
Individual tests can still monkeypatch their own temporary roots. A live app
may be processing real data while pytest runs; tests must not inspect its jobs.
"""
import atexit
import os
import sys
import tempfile
from pathlib import Path

_TEST_RUNTIME=tempfile.TemporaryDirectory(prefix='nisar-pytest-')
os.environ['NISAR_DATA_DIR']=_TEST_RUNTIME.name
atexit.register(_TEST_RUNTIME.cleanup)
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
