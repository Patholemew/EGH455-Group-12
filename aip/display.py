"""Show processed AIP frames and handle window input and cleanup."""

import cv2


def display_frame(frame):
    """Show a frame and return False when Q or Escape is pressed."""
    cv2.imshow("AIP", frame)
    key = cv2.waitKey(1) & 0xFF
    return key not in (ord("q"), ord("Q"), 27)


def close_display():
    """Close the OpenCV display windows."""
    cv2.destroyAllWindows()
