"""Backend log streaming via WebSocket."""

import asyncio
import logging
import threading
from collections import deque
from datetime import datetime
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect


LOG_BUFFER_SIZE = 500
_buffer: deque = deque(maxlen=LOG_BUFFER_SIZE)
_buffer_lock = threading.Lock()


class BufferedHandler(logging.Handler):
    """Log handler that stores records in a shared buffer."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            with _buffer_lock:
                _buffer.append(
                    {
                        "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                    }
                )
        except Exception:
            self.handleError(record)


def get_recent_logs(count: int = 100) -> list[dict]:
    """Get the most recent logs from the buffer."""
    with _buffer_lock:
        return list(_buffer)[-count:]


async def log_ws_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint that streams all backend logs to the client."""
    await websocket.accept()

    initial_logs = get_recent_logs(200)
    for log in initial_logs:
        await websocket.send_json(log)

    try:
        while True:
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
