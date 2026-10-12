"""Save camera intrinsics for the cropped 512x512 AIP image."""

from pathlib import Path

import cv2
import depthai as dai
import numpy as np

from oak_detector import CAMERA_HEIGHT, CAMERA_WIDTH, CROP_ZOOM


OUTPUT_WIDTH = 512
OUTPUT_HEIGHT = 512
CAMERA_SOCKET = dai.CameraBoardSocket.CAM_A
OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "camera_intrinsics.yaml"
)


def centred_crop(width, height, zoom):
    """Return the crop used by OakDetector as (x, y, width, height)."""
    if zoom < 1.0:
        raise ValueError("CROP_ZOOM must be >= 1.0")

    crop_size = int(min(width, height) / zoom)
    # Keep this alignment identical to OakDetector's ImageManip crop.
    crop_size = (crop_size // 16) * 16
    if crop_size <= 0:
        raise ValueError("Calculated crop size must be positive")

    crop_x = (width - crop_size) // 2
    crop_y = (height - crop_size) // 2
    return crop_x, crop_y, crop_size, crop_size


def transform_intrinsics(camera_matrix, crop, output_size):
    """Adjust an intrinsic matrix for a crop followed by a resize."""
    crop_x, crop_y, crop_width, crop_height = crop
    output_width, output_height = output_size
    scale_x = output_width / crop_width
    scale_y = output_height / crop_height

    adjusted = np.asarray(camera_matrix, dtype=np.float64).copy()
    if adjusted.shape != (3, 3):
        raise ValueError("Camera intrinsic matrix must be 3x3")

    adjusted[0, 0] *= scale_x
    adjusted[0, 1] *= scale_x
    adjusted[0, 2] = (adjusted[0, 2] - crop_x) * scale_x
    adjusted[1, 0] *= scale_y
    adjusted[1, 1] *= scale_y
    adjusted[1, 2] = (adjusted[1, 2] - crop_y) * scale_y
    return adjusted


def main():
    crop = centred_crop(CAMERA_WIDTH, CAMERA_HEIGHT, CROP_ZOOM)
    crop_x, crop_y, crop_width, crop_height = crop

    with dai.Device() as device:
        calibration = device.readCalibration()

        # Request factory intrinsics in the coordinate system of the
        # full-resolution frame entering ImageManip.
        source_intrinsics = np.asarray(
            calibration.getCameraIntrinsics(
                CAMERA_SOCKET,
                CAMERA_WIDTH,
                CAMERA_HEIGHT,
            ),
            dtype=np.float64,
        )
        distortion_coeffs = np.asarray(
            calibration.getDistortionCoefficients(CAMERA_SOCKET),
            dtype=np.float64,
        ).reshape(-1, 1)

    camera_intrinsics = transform_intrinsics(
        source_intrinsics,
        crop,
        (OUTPUT_WIDTH, OUTPUT_HEIGHT),
    )

    print(f"Source image: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
    print(
        f"Crop: {crop_width}x{crop_height} at "
        f"({crop_x}, {crop_y})"
    )
    print(f"Output image: {OUTPUT_WIDTH}x{OUTPUT_HEIGHT}")
    print("Source intrinsic matrix:\n", source_intrinsics)
    print("Cropped/resized intrinsic matrix:\n", camera_intrinsics)
    print("Distortion coefficients:\n", distortion_coeffs)

    storage = cv2.FileStorage(str(OUTPUT_PATH), cv2.FILE_STORAGE_WRITE)
    if not storage.isOpened():
        raise OSError(f"Cannot write calibration to {OUTPUT_PATH}")
    try:
        storage.write("camera_socket", "CAM_A")
        storage.write("image_width", OUTPUT_WIDTH)
        storage.write("image_height", OUTPUT_HEIGHT)
        storage.write("source_image_width", CAMERA_WIDTH)
        storage.write("source_image_height", CAMERA_HEIGHT)
        storage.write("crop_x", crop_x)
        storage.write("crop_y", crop_y)
        storage.write("crop_width", crop_width)
        storage.write("crop_height", crop_height)
        storage.write("crop_zoom", CROP_ZOOM)
        storage.write("camera_matrix", camera_intrinsics)
        storage.write("distortion_coefficients", distortion_coeffs)
    finally:
        storage.release()

    print(f"Saved calibration to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
