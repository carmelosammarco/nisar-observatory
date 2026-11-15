"""Bound expensive preview/PNG work without queuing worker threads or arrays."""
from contextvars import ContextVar
from functools import wraps
import threading
from fastapi import HTTPException


class RenderAdmission:
    def __init__(self):
        self._slot = threading.BoundedSemaphore(1)
        self._owner = ContextVar('nisar_render_owner', default=None)

    def __call__(self, function):
        @wraps(function)
        def guarded(*args, **kwargs):
            # PNG generation uses the same visualization resolver internally.
            # Only a nested call on this owning thread may reuse the slot.
            thread = threading.get_ident()
            if self._owner.get() == thread:
                return function(*args, **kwargs)
            if not self._slot.acquire(blocking=False):
                raise HTTPException(429, 'Another map is being prepared. Please wait a moment and retry.', headers={'Retry-After': '1', 'X-NISAR-Render-Busy': '1'})
            token = self._owner.set(thread)
            try:
                return function(*args, **kwargs)
            finally:
                self._owner.reset(token)
                self._slot.release()
        return guarded


render_admission = RenderAdmission()
