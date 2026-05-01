# Copyright (c) 2026 Paul Christopher Cerda
# This source code is licensed under the Business Source License 1.1
# found in the LICENSE.md file in the root directory of this source tree.

"""
Server-Sent Events notification manager.
Broadcasts real-time progress events to all connected browser clients.
Also persists notifications to PostgreSQL for history.
"""

import asyncio
import json
import datetime
from typing import AsyncGenerator, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal, Notification


class NotificationManager:
    """
    In-memory SSE subscriber registry.
    Each connected browser tab gets its own asyncio.Queue.
    """

    def __init__(self):
        self._subscribers: Dict[str, asyncio.Queue] = {}

    def subscribe(self, client_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers[client_id] = q
        return q

    def unsubscribe(self, client_id: str):
        self._subscribers.pop(client_id, None)

    async def broadcast(
        self,
        event_type: str,
        title: str,
        body: str,
        payload: dict = None,
        persist: bool = True,
    ):
        """Push an event to every connected client and optionally save to DB."""
        event = {
            "id": str(datetime.datetime.utcnow().timestamp()),
            "type": event_type,
            "title": title,
            "body": body,
            "payload": payload or {},
            "ts": datetime.datetime.utcnow().isoformat(),
        }

        # Persist to DB
        if persist:
            try:
                async with AsyncSessionLocal() as session:
                    notif = Notification(
                        type=event_type,
                        title=title,
                        body=body,
                        payload=payload or {},
                    )
                    session.add(notif)
                    await session.commit()
            except Exception as e:
                print(f"[NOTIF] DB persist failed: {e}")

        # Push to all live SSE clients
        dead = []
        for cid, q in list(self._subscribers.items()):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(cid)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.unsubscribe(cid)

    async def send_to(self, client_id: str, event: dict):
        """Send to a specific client only (e.g. the one who triggered ingestion)."""
        q = self._subscribers.get(client_id)
        if q:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def subscriber_count(self) -> int:
        return len(self._subscribers)


# Singleton used throughout the app
notif_manager = NotificationManager()


async def sse_event_generator(client_id: str) -> AsyncGenerator[str, None]:
    """
    Async generator consumed by FastAPI's StreamingResponse.
    Yields SSE-formatted strings.
    """
    q = notif_manager.subscribe(client_id)

    # Send a "connected" heartbeat immediately
    yield _format_sse({
        "type": "connected",
        "title": "Connected",
        "body": f"Listening for notifications (client {client_id[:8]})",
        "ts": datetime.datetime.utcnow().isoformat(),
    })

    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=25.0)
                yield _format_sse(event)
            except asyncio.TimeoutError:
                # Keep-alive heartbeat every 25s so proxies don't close the connection
                yield ": heartbeat\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        notif_manager.unsubscribe(client_id)


def _format_sse(data: dict) -> str:
    """Format a dict as an SSE message."""
    event_type = data.get("type", "message")
    payload = json.dumps(data)
    return f"event: {event_type}\ndata: {payload}\n\n"
