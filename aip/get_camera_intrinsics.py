import depthai as dai
import numpy as np

with dai.Device() as device:
    calibData = device.readCalibration()
    
    # Get intrinsics for a specific camera socket and resolution (e.g., RGB camera on CAM_A at 1920x1085 or 1280x720)
    # CAM_A = RGB camera, CAM_B / CAM_C = Left/Right Mono cameras
    camera_intrinsics = np.array(calibData.getCameraIntrinsics(dai.CameraBoardSocket.CAM_A, 1920, 1080))
    distortion_coeffs = np.array(calibData.getDistortionCoefficients(dai.CameraBoardSocket.CAM_A))
    
    print("Intrinsic Matrix:\n", camera_intrinsics)
    print("Distortion Coefficients:\n", distortion_coeffs)
