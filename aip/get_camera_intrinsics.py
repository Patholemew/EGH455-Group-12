"""Save camera intrinsics for the cropped AIP detector image."""

from pathlib import Path

import cv2
import depthai as dai
import numpy as np

from oak_detector import CROP_BASE_SIZE, CROP_POSITION, CROP_ZOOM


# This must match the input resolution of the model selected in aip_main.py.
OUTPUT_WIDTH = 640
OUTPUT_HEIGHT = 640
CAMERA_SOCKET = dai.CameraBoardSocket.CAM_A
OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "camera_intrinsics.yaml"
)


def detector_crop(base_size, zoom, position):
    """Return OakDetector's square crop as (x, y, width, height)."""
    if zoom < 1.0:
        raise ValueError("CROP_ZOOM must be >= 1.0")

    crop_size = int(base_size / zoom)
    # Keep this alignment identical to OakDetector's ImageManip crop.
    crop_size = (crop_size // 16) * 16
    if crop_size <= 0:
        raise ValueError("Calculated crop size must be positive")

    crop_x = (base_size - crop_size) // 2
    if position == "center":
        crop_y = (base_size - crop_size) // 2
    elif position == "bottom":
        crop_y = base_size - crop_size
    else:
        raise ValueError(
            f"Invalid CROP_POSITION: {position}. "
            'Use "center" or "bottom".'
        )

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
    source_width = CROP_BASE_SIZE
    source_height = CROP_BASE_SIZE
    crop = detector_crop(CROP_BASE_SIZE, CROP_ZOOM, CROP_POSITION)
    crop_x, crop_y, crop_width, crop_height = crop

    with dai.Device() as device:
        calibration = device.readCalibration()

        # Request factory intrinsics in the coordinate system of the
        # full-resolution frame entering ImageManip.
        source_intrinsics = np.asarray(
            calibration.getCameraIntrinsics(
                CAMERA_SOCKET,
                source_width,
                source_height,
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

    print(f"Source image: {source_width}x{source_height}")
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
        storage.write("source_image_width", source_width)
        storage.write("source_image_height", source_height)
        storage.write("crop_x", crop_x)
        storage.write("crop_y", crop_y)
        storage.write("crop_width", crop_width)
        storage.write("crop_height", crop_height)
        storage.write("crop_zoom", CROP_ZOOM)
        storage.write("crop_position", CROP_POSITION)
        storage.write("camera_matrix", camera_intrinsics)
        storage.write("distortion_coefficients", distortion_coeffs)
    finally:
        storage.release()

    print(f"Saved calibration to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
