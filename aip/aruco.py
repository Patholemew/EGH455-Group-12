"""Display camera frames for the ArUco processing module."""

import cv2


def display_frame(frame):
    """Show a BGR camera frame and return False when the user requests exit."""
    cv2.imshow("AIP - ArUco", frame)
    key = cv2.waitKey(1) & 0xFF
    return key not in (ord("q"), ord("Q"), 27)


def close_display():
    """Close the OpenCV display windows."""
    cv2.destroyAllWindows()
