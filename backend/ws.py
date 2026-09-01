"""WebSocket endpoint for streaming live tool output while a scan runs."""
from __future__ import annotations

import asyncio
import threading
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from oculus import state
from oculus.models import Status
from oculus.orchestrator import Orchestrator
from oculus.tools.base import CANCELLED_EXIT_CODE

router = APIRouter()

# Tracks the cancel_event for every currently-running tool, keyed by
# (eng_id, item_id) — a run keeps executing server-side after its own
# WebSocket disconnects (see the comment below), so a stop request needs
# somewhere to find it that isn't tied to that connection. Registered right
# before the worker thread starts, removed in its `finally`. Read/written
# from the asyncio event loop thread (register/unregister, and the REST
# cancel endpoint in backend/routers/items.py) and never mutated from the
# worker thread itself, so no extra locking is needed — dict access itself
# is already atomic under the GIL for these single get/set/del operations.
_RUNNING: dict[tuple[str, str], threading.Event] = {}


def cancel_run(eng_id: str, item_id: str) -> bool:
    """Request a stop for the tool currently running on this item, if any.

    Returns True if a run was found and signaled, False if nothing is
    running there (nothing to do — not an error, the item may have already
    finished on its own between the tester clicking Stop and this call).
    """
    event = _RUNNING.get((eng_id, item_id))
    if event is None:
        return False
    event.set()
    return True


@router.websocket("/ws/engagements/{eng_id}/items/{item_id}/run")
async def run_tool_ws(websocket: WebSocket, eng_id: str, item_id: str) -> None:
    await websocket.accept()

    try:
        engagement = state.load(eng_id)
    except FileNotFoundError:
        await websocket.send_json({"type": "error", "message": f"Engagement '{eng_id}' not found"})
        await websocket.close()
        return

    item = engagement.get_item(item_id)
    if item is None:
        await websocket.send_json({"type": "error", "message": f"Checklist item '{item_id}' not found"})
        await websocket.close()
        return

    try:
        config = await websocket.receive_json()
    except WebSocketDisconnect:
        return

    tool_name = config.get("tool")
    fast = bool(config.get("fast", False))
    custom_command_raw = config.get("custom_command")
    custom_command = custom_command_raw.split() if custom_command_raw else None

    if not tool_name:
        await websocket.send_json({"type": "error", "message": "Missing 'tool' in start message"})
        await websocket.close()
        return

    # A run started from this item keeps executing server-side even after
    # the tester closes the Run Tool dialog (the worker thread below isn't
    # tied to this WebSocket's lifetime) — so if they reopen the dialog and
    # hit Run again before the first one finishes, refuse rather than
    # silently starting a second overlapping subprocess that would race the
    # first on item.tool_outputs/findings and corrupt either result.
    if item.status == Status.RUNNING:
        await websocket.send_json({
            "type": "error",
            "message": f"{item.id} already has a tool running in the background — "
                       "wait for it to finish (the checklist sidebar shows its progress) "
                       "before starting another.",
        })
        await websocket.close()
        return

    # Persisted immediately, before the (possibly slow) subprocess even
    # starts — so a tester who closes this dialog and navigates elsewhere
    # still sees "running" reflected in the checklist on their next fetch,
    # instead of the item looking exactly like it did before they clicked
    # Run (indistinguishable from "nothing happened").
    item.status = Status.RUNNING
    item.started_at = item.started_at or datetime.now()
    state.save(engagement)

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    result_holder: dict = {}
    cancel_event = threading.Event()
    run_key = (eng_id, item_id)

    def on_line(line: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, {"type": "line", "data": line})

    def worker() -> None:
        try:
            orchestrator = Orchestrator(engagement)
            result = orchestrator.run_tool(
                item, tool_name, on_line=on_line,
                custom_command=custom_command, fast=fast,
                cancel_event=cancel_event,
            )
            state.save(engagement)
            result_holder["result"] = result
        except Exception as exc:  # noqa: BLE001 — surfaced to the client, not swallowed
            result_holder["error"] = str(exc)
        finally:
            _RUNNING.pop(run_key, None)
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "done"})

    _RUNNING[run_key] = cancel_event
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    try:
        while True:
            message = await queue.get()
            if message["type"] == "done":
                if "error" in result_holder:
                    await websocket.send_json({"type": "error", "message": result_holder["error"]})
                else:
                    result = result_holder["result"]
                    await websocket.send_json({
                        "type": "done",
                        "item": item.model_dump(mode="json"),
                        "result": {
                            "tool": result.tool,
                            "command": result.command,
                            "exit_code": result.exit_code,
                            "elapsed_seconds": result.elapsed_seconds,
                            "simulated": result.simulated,
                            "success": result.success,
                            "cancelled": result.exit_code == CANCELLED_EXIT_CODE,
                        },
                    })
                break
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
