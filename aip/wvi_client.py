import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

WVI_URL = os.environ.get("WVI_URL", "http://127.0.0.1:8000")
FRAME_PATH = Path(os.environ.get("WVI_FRAME_FILE", "/dev/shm/uav/liveimage.jpg"))
SNAPSHOT_DIR = Path(os.environ.get("WVI_SNAPSHOT_DIR", "/var/lib/uav-wvi/snapshots"))


def publish_live_frame(jpeg_bytes, frame_id, captured_at):
    FRAME_PATH.parent.mkdir(parents=True, exist_ok=True)

    temporary = FRAME_PATH.with_suffix(".tmp")
    temporary.write_bytes(jpeg_bytes)
    os.replace(temporary, FRAME_PATH)

    meta = FRAME_PATH.with_suffix(".json")
    temporary_meta = FRAME_PATH.with_suffix(".json.tmp")
    temporary_meta.write_text(json.dumps({"frame_id": frame_id, "captured_at": captured_at}))
    os.replace(temporary_meta, meta)


def save_capture(jpeg_bytes, filename):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / filename
    if path.exists():
        return
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(jpeg_bytes)
    os.replace(temporary, path)


def post_detection(payload):
    request = Request(WVI_URL + "/api/target", data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=2) as response:
        return response.status