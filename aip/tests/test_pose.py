"""Synthetic geometry checks; no camera or display required."""

import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pose import PoseEstimator


class PoseTests(unittest.TestCase):
    def setUp(self):
        self.estimator = PoseEstimator(0.2)
        self.frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    def test_camera_position_and_ids(self):
        corners = []
        expected = []
        for rvec, tvec in [([2.9, 0.1, 0.2], [0.1, -0.05, 1.2]),
                           ([2.7, -0.2, 0.1], [-0.2, 0.1, 1.8])]:
            rvec = np.array(rvec, dtype=float)
            tvec = np.array(tvec, dtype=float)
            points, _ = cv2.projectPoints(
                self.estimator.object_points, rvec, tvec,
                self.estimator.camera_matrix, self.estimator.distortion)
            corners.append(points.reshape(1, 4, 2))
            rotation, _ = cv2.Rodrigues(rvec)
            expected.append(-rotation.T @ tvec)
        poses = self.estimator.estimate(self.frame, corners, np.array([[7], [12]]))
        self.assertEqual([p.marker_id for p in poses], [7, 12])
        for pose, position in zip(poses, expected):
            np.testing.assert_allclose(pose.camera_position_m, position, atol=1e-5)
        self.estimator.draw(self.frame.copy(), poses)

    def test_no_detection(self):
        self.assertEqual(self.estimator.estimate(self.frame, [], None), [])

    def test_wrong_resolution(self):
        with self.assertRaises(ValueError):
            self.estimator.estimate(self.frame[:360], [], None)

    def test_invalid_size(self):
        for size in (0, -0.2, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                PoseEstimator(size)


if __name__ == "__main__":
    unittest.main()
