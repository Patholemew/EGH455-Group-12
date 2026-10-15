import depthai as dai
import time

FPS = 30
SIZE = 640

with dai.Pipeline() as pipeline:

    camera = (
        pipeline
        .create(dai.node.Camera)
        .build(
            dai.CameraBoardSocket.CAM_A,
            sensorFps=FPS,
        )
    )

    output = camera.requestOutput(
        size=(SIZE, SIZE),
        type=dai.ImgFrame.Type.BGR888p,
        resizeMode=dai.ImgResizeMode.CROP,
    )

    queue = output.createOutputQueue()

    print(
        "USB speed:",
        pipeline.getDefaultDevice().getUsbSpeed().name
    )

    pipeline.start()

    count = 0
    start = time.monotonic()

    while time.monotonic() - start < 10:
        queue.get()
        count += 1

    elapsed = time.monotonic() - start

    print(f"Camera FPS: {count / elapsed:.1f}")