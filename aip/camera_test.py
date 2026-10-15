import cv2
import depthai as dai

with dai.Pipeline() as pipeline:

    cam = pipeline.create(dai.node.Camera).build(
        dai.CameraBoardSocket.CAM_A
    )

    video_queue = (
        cam.requestOutput((512, 512))
        .createOutputQueue()
    )

    pipeline.start()

    while pipeline.isRunning():
        msg = video_queue.get()
        frame = msg.getCvFrame()

        cv2.imshow("camera test", frame)

        if cv2.waitKey(1) == ord("q"):
            break
        