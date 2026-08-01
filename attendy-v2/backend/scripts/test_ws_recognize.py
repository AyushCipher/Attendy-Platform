"""Manual end-to-end smoke test for the Phase 5 WS pipeline: connects to both
/ws/attendance-feed and /ws/recognize, streams a jittered frame sequence for an
already-enrolled student, and confirms both the per-frame recognition status and
the cross-connection real-time broadcast fire correctly. Not a pytest test --
run directly against a live `uvicorn` + Postgres instance:

    venv/Scripts/python scripts/test_ws_recognize.py <frames_dir> <admin_email> <admin_password>
"""
import asyncio
import json
import sys
from pathlib import Path

import httpx
import websockets

API = "http://127.0.0.1:8000/api"
WS = "ws://127.0.0.1:8000"


async def main():
    frames_dir = Path(sys.argv[1])
    email, password = sys.argv[2], sys.argv[3]

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
        token = resp.json()["access_token"]

    feed_events: list[dict] = []

    async def listen_feed():
        async with websockets.connect(f"{WS}/ws/attendance-feed?token={token}") as ws:
            async for message in ws:
                feed_events.append(json.loads(message))

    feed_task = asyncio.create_task(listen_feed())
    await asyncio.sleep(0.3)  # let the feed connection establish first

    frame_files = sorted(frames_dir.glob("frame_*.jpg"))
    print(f"Streaming {len(frame_files)} frames over /ws/recognize...")

    async with websockets.connect(f"{WS}/ws/recognize?token={token}") as ws:
        for path in frame_files:
            await ws.send(path.read_bytes())
            response = json.loads(await ws.recv())
            print(f"  {path.name}: {response['faces']}")
            await asyncio.sleep(0.2)

    await asyncio.sleep(0.5)
    feed_task.cancel()

    print()
    print(f"attendance-feed received {len(feed_events)} broadcast(s):")
    for event in feed_events:
        print(" ", event)

    if not feed_events:
        print("\nFAIL: no attendance_confirmed broadcast received")
        sys.exit(1)
    print("\nPASS: real-time confirmation broadcast received")


if __name__ == "__main__":
    asyncio.run(main())
