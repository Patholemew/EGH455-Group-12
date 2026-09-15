# camera.py

import depthai as dai


class Camera:
    def __init__(self):
        self.pipeline = dai.Pipeline()

        # Camera setup (CAM_A is colour, B and C is greyscale stereo cameras)
        self.cam = self.pipeline.create(dai.node.Camera).build(
            dai.CameraBoardSocket.CAM_A
        )
        
        # Request an RGB output
        self.frame_queue = self.cam.requestOutput(
            (1280, 720)
        ).createOutputQueue(
            maxSize=4,
            blocking=False
        )

        self.pipeline.start()

    def get_frame(self):
        # Get next DepthAI frame here
        # Then convert using getCvFrame()
        
        frame = self.frame_queue.get()

        return frame.getCvFrame()

    def close(self):
        self.pipeline.stop()