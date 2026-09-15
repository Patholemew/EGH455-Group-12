"""Detect ArUco markers and annotate camera frames."""

import cv2


# Must match the dictionary used to generate the physical markers.
ARUCO_DICTIONARY = cv2.aruco.DICT_5X5_50
_detector = cv2.aruco.ArucoDetector(
    cv2.aruco.getPredefinedDictionary(ARUCO_DICTIONARY),
    cv2.aruco.DetectorParameters(),
)


def detect_aruco(frame):
    """Return (corners, ids) for a BGR or grayscale frame without modifying it.

    Each corners entry has shape (1, 4, 2), with pixel coordinates ordered
    clockwise from the marker's top-left corner. IDs have shape (N, 1), or
    are None when no markers are detected.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    corners, ids, _ = _detector.detectMarkers(gray)
    return corners, ids


def draw_aruco(frame, corners, ids):
    """Return a copy of the frame with marker outlines and IDs drawn on it."""
    annotated = frame.copy()
    if ids is not None:
        cv2.aruco.drawDetectedMarkers(annotated, corners, ids)
    return annotated
