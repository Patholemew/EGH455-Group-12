"""Write a JPEG frame atomically. AIP calls this after annotating each frame."""
import os
from pathlib import Path
import json


def publish_frame(jpeg_bytes, destination, *, frame_id=None, captured_at=None):
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(jpeg_bytes)
    os.replace(temporary, path)

    if captured_at is not None:
        meta = path.with_suffix(".json")
        temporary_meta = path.with_suffix(".json.tmp")
        temporary_meta.write_text(json.dumps({"frame_id": frame_id, "captured_at": captured_at}))
        os.replace(temporary_meta, meta)