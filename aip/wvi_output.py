""" AIP output formatting for WVI. """
import cv2
import time

# Make a lightweight dictionary of AIP results for WVI. This contains timestamp, detected valves, gauge reading and detected ArUco markers.
def make_wvi_data(result, gauge_reading, marker_poses, frame_timestamp):
    """Create lightweight AIP results packet."""

    # List of detected valves with their state and pixel coordinates of the centre.
    valves = []

    for valve in result["valves"]:
        valves.append({
            "state": valve["state"],
            "centre_px": valve["centre"],
        })

    # Gauge reading is a dictionary with type, validity, angle and measurement. If no gauge is detected, this will be None.
    if gauge_reading is not None:
        gauge = {
            "type": gauge_reading["type"],
            "valid": gauge_reading["valid"],
            "angle": gauge_reading.get("angle"),
            "measurement": gauge_reading.get("measurement"),
        }
    else:
        gauge = None

    # List of detected ArUco markers with their ID and camera position in meters relative to the marker. If no markers are detected, this will be an empty list.
    markers = []

    for pose in marker_poses:
        x, y, z = pose.camera_position_m

        markers.append({
            "id": pose.marker_id,
            "camera_position_m": {
                "x": x,
                "y": y,
                "z": z,
            },
        })

    # Return a dictionary containing all the AIP outputs for WVI.
    return {
        "timestamp": frame_timestamp,
        "valves": valves,
        "gauge": gauge,
        "aruco": markers,
    }

# Encode OpenCV frame as JPEG bytes. Returns None if encoding fails.
def encode_frame(frame):
    """Encode OpenCV frame as JPEG bytes."""

    try:
        success, buffer = cv2.imencode(".jpg", frame)

        if not success:
            return None

        return buffer.tobytes()

    except cv2.error as error:
        print(f"Frame encoding failed: {error}")
        return None

# Prepare all AIP outputs for WVI. Returns a tuple of (data, image), where data is a dictionary of results and image is the annotated frame encoded as JPEG bytes.
def prepare_wvi_output(
    result,
    gauge_reading,
    marker_poses,
    frame_timestamp,
    annotated_frame,
):
    """Prepare all AIP outputs for WVI."""

    data = make_wvi_data(
        result,
        gauge_reading,
        marker_poses,
        frame_timestamp,
    )

    image = encode_frame(
        annotated_frame
    )

    return data, image