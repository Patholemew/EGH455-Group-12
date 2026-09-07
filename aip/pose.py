"""Estimate camera position in each ArUco marker's coordinate system."""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


CALIBRATION_PATH = Path(__file__).resolve().parent.parent / "config" / "camera_intrinsics.yaml"


@dataclass
class MarkerPose:
    marker_id: int
    camera_position_m: np.ndarray
    rvec: np.ndarray  # Marker-to-camera rotation, for drawing axes.
    tvec: np.ndarray  # Marker origin in camera coordinates, metres.


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

    def estimate(self, frame, corners, ids):
        """Return current-frame poses; an absent marker has no entry."""
        if (frame.shape[1], frame.shape[0]) != self.image_size:
            raise ValueError(f"Frame size must match calibration {self.image_size}")
        if ids is None:
            return []
        poses = []
        for marker_corners, marker_id in zip(corners, ids.flatten()):
            ok, rvec, tvec = cv2.solvePnP(
                self.object_points,
                np.asarray(marker_corners, dtype=np.float64).reshape(4, 2),
                self.camera_matrix, self.distortion,
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

    def draw(self, annotated, poses):
        """Draw marker axes and camera positions onto the annotated frame."""
        for row, pose in enumerate(poses):
            cv2.drawFrameAxes(annotated, self.camera_matrix, self.distortion,
                              pose.rvec, pose.tvec, self.marker_size_m / 2)
            x, y, z = pose.camera_position_m
            label = f"ID {pose.marker_id}: camera X {x:+.3f} Y {y:+.3f} Z {z:+.3f} m"
            origin = (10, 30 + row * 30)
            cv2.putText(annotated, label, origin, cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(annotated, label, origin, cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (255, 255, 255), 1, cv2.LINE_AA)
        return annotated
