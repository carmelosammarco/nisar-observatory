"""Cooperative worker cancellation, isolated to the current execution context.

Cancellation is control flow, not a bad scientific input. A BaseException avoids
conversion to needs_input/failed by broad library error handlers. Only the job
supervisor catches it. A running NumPy/GDAL/network call finishes before its next
checkpoint; completed result bundles and source files are never removed here.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

_CURRENT = ContextVar('nisar_execution_cancel', default=None)

class ProcessingCancelled(BaseException):
    """The owner requested that this execution stop at a safe boundary."""


def checkpoint(cancel=None):
    callback = cancel if cancel is not None else _CURRENT.get()
    if callback is not None and callback():
        raise ProcessingCancelled('Cancelled by user.')


@contextmanager
def execution_scope(cancel):
    token = _CURRENT.set(cancel)
    try:
        checkpoint()
        yield
    finally:
        _CURRENT.reset(token)


def cancellable(function):
    """Add entry/exit boundaries without changing a numerical implementation."""
    @wraps(function)
    def guarded(*args, **kwargs):
        checkpoint()
        result = function(*args, **kwargs)
        checkpoint()
        return result
    return guarded
