""" AIP output formatting for WVI. """
import cv2
import time

# Make a lightweight dictionary of AIP results for WVI. This contains timestamp, detected valves, gauge reading and detected ArUco markers.
def make_wvi_data(result, gauge_reading, marker_poses):
    """Create lightweight AIP results packet."""

    valves = []

    for valve in result["valves"]:
        valves.append({
            "state": valve["state"],
            "centre": valve["centre"],
        })

    if gauge_reading is not None:
        gauge = {
            "type": gauge_reading["type"],
            "valid": gauge_reading["valid"],
            "angle": gauge_reading.get("angle"),
            "measurement": gauge_reading.get("measurement"),
        }
    else:
        gauge = None

    markers = []

    for pose in marker_poses:
        x, y, z = pose.camera_position_m

        markers.append({
            "id": pose.marker_id,
            "x": x,
            "y": y,
            "z": z,
        })

    return {
        "timestamp": time.time(),
        "valves": valves,
        "gauge": gauge,
        "aruco": markers,
    }

# Encode OpenCV frame as JPEG bytes. Returns None if encoding fails.
def encode_frame(frame):
    """Encode OpenCV frame as JPEG bytes."""

    success, buffer = cv2.imencode(".jpg", frame)

    if not success:
        return None

    return buffer.tobytes()

# Prepare all AIP outputs for WVI. Returns a tuple of (data, image), where data is a dictionary of results and image is the annotated frame encoded as JPEG bytes.
def prepare_wvi_output(
    result,
    gauge_reading,
    marker_poses,
    annotated_frame,
):
    """Prepare all AIP outputs for WVI."""

    data = make_wvi_data(
        result,
        gauge_reading,
        marker_poses,
    )

    image = encode_frame(
        annotated_frame
    )

    return data, image