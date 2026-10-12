import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

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

last_sent = 0.0
frame_id = 0
CAPTURE_INTERVAL_SECONDS = 1.0
last_captured = {}

VALVE_STATES = {"Open Valve": "open", "Closed Valve": "closed"}


def send_aip_output(aip_data, aip_image):
    global last_sent, frame_id

    now = time.monotonic()
    if now - last_sent < 0.1:
        return
    last_sent = now

    timestamp = aip_data["timestamp"]

    if aip_image is not None:
        publish_live_frame(aip_image, frame_id, timestamp)
        frame_id += 1

    detections = []

    for number, valve in enumerate(aip_data["valves"], start=1):
        detections.append({
            "event_id": f"valve-{number}",
            "type": "valve",
            "state": VALVE_STATES.get(valve["state"], "unknown")
        })

    gauge = aip_data["gauge"]
    if gauge is not None and gauge["valid"] and gauge["measurement"] is not None:
        detections.append({
            "event_id": "gauge-1",
            "type": "gauge",
            "reading": float(gauge["measurement"]),
            "unit": "BAR"
        })

    for marker in aip_data["aruco"]:
        position = marker["camera_position_m"]
        detections.append({
            "event_id": f"aruco-{marker['id']}",
            "type": "aruco",
            "marker_id": int(marker["id"]),
            "position_m": {
                "x": float(position["x"]),
                "y": float(position["y"]),
                "z": float(position["z"])
            },
            "coordinate_frame": "camera position in marker frame (m)"
        })

    # Keep independent historical captures without saving every video frame.
    detections = [
        detection for detection in detections
        if now - last_captured.get(detection["event_id"], float("-inf"))
        >= CAPTURE_INTERVAL_SECONDS
    ]
    filename = None
    if detections and aip_image is not None:
        # Targets observed in the same frame share that frame's immutable image.
        filename = "capture-" + uuid4().hex + ".jpg"
        save_capture(aip_image, filename)

    for detection in detections:
        detection["captured_at"] = timestamp
        detection["confidence"] = None
        detection["image_filename"] = filename

        try:
            post_detection(detection)
            last_captured[detection["event_id"]] = now
        except Exception as error:
            print(f"WVI post failed: {error}", flush=True)
