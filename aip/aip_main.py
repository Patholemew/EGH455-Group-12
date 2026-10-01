"""Entry point for the AIP subsystem."""
import time
from datetime import datetime, timezone

import cv2
import depthai as dai

from wvi_client import publish_live_frame


def main():
    pipeline = dai.Pipeline()
    camRgb = pipeline.create(dai.node.ColorCamera)
    camRgb.setBoardSocket(dai.CameraBoardSocket.CAM_A)
    camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
    camRgb.setVideoSize(960, 540)

    xout = pipeline.create(dai.node.XLinkOut)
    xout.setStreamName("rgb")
    camRgb.video.link(xout.input)

    with dai.Device(pipeline) as device:
        queue = device.getOutputQueue("rgb", maxSize=4, blocking=False)
        frame_id = 0
        while True:
            tick = time.monotonic()
            packet = queue.get()
            ok, buffer = cv2.imencode(".jpg", packet.getCvFrame(),
                                      [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if ok:
                publish_live_frame(buffer.tobytes(), frame_id,
                                   datetime.now(timezone.utc).isoformat())
                frame_id += 1
            time.sleep(max(0, 0.1 - (time.monotonic() - tick)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("AIP stopped.")