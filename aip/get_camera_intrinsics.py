from pathlib import Path

import cv2
import depthai as dai
import numpy as np

with dai.Device() as device:
    calibData = device.readCalibration()
    
    # Match the RGB output resolution in camera.py.
    # CAM_A = RGB camera, CAM_B / CAM_C = Left/Right Mono cameras
    camera_intrinsics = np.array(calibData.getCameraIntrinsics(dai.CameraBoardSocket.CAM_A, 1280, 720))
    distortion_coeffs = np.array(calibData.getDistortionCoefficients(dai.CameraBoardSocket.CAM_A))
    
    print("Intrinsic Matrix:\n", camera_intrinsics)
    print("Distortion Coefficients:\n", distortion_coeffs)

    output_path = Path(__file__).resolve().parent.parent / "config" / "camera_intrinsics.yaml"
    storage = cv2.FileStorage(str(output_path), cv2.FILE_STORAGE_WRITE)
    if not storage.isOpened():
        raise OSError(f"Cannot write calibration to {output_path}")
    try:
        storage.write("camera_socket", "CAM_A")
        storage.write("image_width", 1280)
        storage.write("image_height", 720)
        storage.write("camera_matrix", camera_intrinsics)
        storage.write("distortion_coefficients", distortion_coeffs)
    finally:
        storage.release()
    print(f"Saved calibration to {output_path}")
