"""Estimate camera position in each ArUco marker's coordinate system."""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

# Path to the camera calibration file. The calibration must include a 3x3 matrix, distortion coefficients and image size.
CALIBRATION_PATH = Path(__file__).resolve().parent.parent / "config" / "camera_intrinsics.yaml"

# Dataclass to hold the pose of a detected marker relative to the camera.
@dataclass
class MarkerPose:
    marker_id: int
    camera_position_m: np.ndarray
    rvec: np.ndarray  # Marker-to-camera rotation, for drawing axes.
    tvec: np.ndarray  # Marker origin in camera coordinates, metres.

# Class to estimate the camera's position relative to detected ArUco markers.
class PoseEstimator:
    def __init__(self, marker_size_m, calibration_path=CALIBRATION_PATH):
        if not np.isfinite(marker_size_m) or marker_size_m <= 0:
            raise ValueError("Marker side length must be a positive finite number")
        self.marker_size_m = marker_size_m
        storage = cv2.FileStorage(str(calibration_path), cv2.FILE_STORAGE_READ)
        if not storage.isOpened():
            raise ValueError(f"Cannot read calibration: {calibration_path}")
        try:
            self.camera_matrix = storage.getNode("camera_matrix").mat()
            self.distortion = storage.getNode("distortion_coefficients").mat()
            self.image_size = (
                int(storage.getNode("image_width").real()),
                int(storage.getNode("image_height").real()),
            )
        finally:
            storage.release()
        if (self.camera_matrix is None or self.camera_matrix.shape != (3, 3)
                or self.distortion is None or min(self.image_size) <= 0):
            raise ValueError("Calibration must include a 3x3 matrix, distortion and image size")
        half = marker_size_m / 2
        # IPPE_SQUARE order matches ArUco's top-left, top-right, bottom-right,
        # bottom-left. Marker +X is right, +Y up, +Z out of its printed face.
        self.object_points = np.array([
            [-half, half, 0], [half, half, 0],
            [half, -half, 0], [-half, -half, 0],
        ], dtype=np.float64)

    # Return the camera intrinsics adjusted to the frame's dimensions, accounting for letterboxing. The returned matrix is float64.
    def camera_matrix_for(self, frame):
        """Return intrinsics adjusted to the frame's letterboxed dimensions."""
        if frame.ndim < 2 or frame.shape[0] <= 0 or frame.shape[1] <= 0:
            raise ValueError("Frame must have positive width and height")

        frame_width, frame_height = frame.shape[1], frame.shape[0]
        calibration_width, calibration_height = self.image_size

        scale = min(
            frame_width / calibration_width,
            frame_height / calibration_height,
        )
        padding_x = (frame_width - calibration_width * scale) / 2
        padding_y = (frame_height - calibration_height * scale) / 2

        adjusted = self.camera_matrix.astype(np.float64).copy()
        adjusted[0, 0] *= scale
        adjusted[1, 1] *= scale
        adjusted[0, 2] = adjusted[0, 2] * scale + padding_x
        adjusted[1, 2] = adjusted[1, 2] * scale + padding_y
        return adjusted

    # Estimate the camera's position relative to each detected marker. Returns a list of MarkerPose objects, one for each detected marker.
    def estimate(self, frame, corners, ids):
        """Return current-frame poses; an absent marker has no entry."""
        camera_matrix = self.camera_matrix_for(frame)
        if ids is None:
            return []
        poses = []
        for marker_corners, marker_id in zip(corners, ids.flatten()):
            ok, rvec, tvec = cv2.solvePnP(
                self.object_points,
                np.asarray(marker_corners, dtype=np.float64).reshape(4, 2),
                camera_matrix, self.distortion,
                flags=cv2.SOLVEPNP_IPPE_SQUARE,
            )
            if not ok or not np.isfinite(rvec).all() or not np.isfinite(tvec).all():
                continue
            rotation, _ = cv2.Rodrigues(rvec)
            if np.any((rotation @ self.object_points.T + tvec)[2] <= 0):
                continue
            # Invert the marker-to-camera transform to locate the camera.
            position = (-rotation.T @ tvec).reshape(3)
            poses.append(MarkerPose(int(marker_id), position, rvec, tvec))
        return poses

    # Draw the marker axes and camera positions onto the annotated frame. Returns the annotated frame.
    def draw(self, annotated, poses):
        """Draw marker axes and camera positions onto the annotated frame."""
        camera_matrix = self.camera_matrix_for(annotated)
        for row, pose in enumerate(poses):
            cv2.drawFrameAxes(annotated, camera_matrix, self.distortion,
                              pose.rvec, pose.tvec, self.marker_size_m / 2)
            x, y, z = pose.camera_position_m
            label = f"ID {pose.marker_id}: camera X {x:+.3f} Y {y:+.3f} Z {z:+.3f} m"
            origin = (10, 30 + row * 30)
            cv2.putText(annotated, label, origin, cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(annotated, label, origin, cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (255, 255, 255), 1, cv2.LINE_AA)
        return annotated
