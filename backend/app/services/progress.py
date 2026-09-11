"""Progress tracking for the streaming SSE endpoint.

Each research thread owns a list of :class:`ProgressEvent` entries.
Nodes (or the orchestrator wrapper) write events via ``append_event``;
the streaming endpoint yields them to the client.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from pydantic import BaseModel


class ProgressEvent(BaseModel):
    step: str
    message: str
    timestamp: float = 0.0
    done: bool = True


@dataclass
class ThreadProgress:
    events: list[ProgressEvent] = field(default_factory=list)
    complete: bool = False
    error: bool = False
    error_message: str = ""
    start_time: float = field(default_factory=time.monotonic)


_lock = threading.Lock()
_store: dict[str, ThreadProgress] = {}


def _progress(thread_id: str) -> ThreadProgress:
    if thread_id not in _store:
        _store[thread_id] = ThreadProgress()
    return _store[thread_id]


def append_event(thread_id: str, step: str, message: str, *, done: bool = True) -> None:
    with _lock:
        p = _progress(thread_id)
        p.events.append(
            ProgressEvent(
                step=step,
                message=message,
                timestamp=time.monotonic() - p.start_time,
                done=done,
            )
        )


def mark_complete(thread_id: str) -> None:
    with _lock:
        _progress(thread_id).complete = True


def mark_error(thread_id: str, msg: str) -> None:
    with _lock:
        p = _progress(thread_id)
        p.complete = True
        p.error = True
        p.error_message = msg


def get_events(thread_id: str) -> list[ProgressEvent]:
    with _lock:
        return list(_progress(thread_id).events)


def is_complete(thread_id: str) -> bool:
    with _lock:
        return _progress(thread_id).complete


def clear(thread_id: str) -> None:
    with _lock:
        _store.pop(thread_id, None)
