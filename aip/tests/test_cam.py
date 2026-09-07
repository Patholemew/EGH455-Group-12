import cv2
import depthai as dai

# Create pipeline
pipeline =dai.Pipeline()
#Properties
camRgb =pipeline.create(dai.node.ColorCamera)
camRgb.setBoardSocket(dai.CameraBoardSocket.CAM_A)
camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
#Define spource and output
xoutRgb =pipeline.create(dai.node.XLinkOut)
xoutRgb.setStreamName("rgb")
camRgb.video.link(xoutRgb.input)

# Connect to device and start pipeline
with dai.Device(pipeline) as device:
    print('Connected cameras:', device.getConnectedCameraFeatures())
    # Print out usb speed
    print('Usb speed:', device.getUsbSpeed().name)
    # Bootloader version
    if device.getBootloaderVersion() is not None:
        print('Bootloader version:', device.getBootloaderVersion())
    # Device name
    print('Device name:', device.getDeviceName())
    # Output queue will be used to get the rgb frames from the output defined above
    qRgb =device.getOutputQueue(name="rgb", maxSize=30, blocking=False)
    inRgb =qRgb.get() # blocking call, will wait until a new data has arrived
    # save a picture using OpenCV
    cv2.imwrite('test_image.jpg', inRgb.getCvFrame())