"""Console output for AIP detection results."""


def print_results(result, gauge_reading, marker_poses=()):
    """Print current AIP detection results."""

    # Gauge reading
    if gauge_reading is None:
        print("No reliable gauge detected")

    elif gauge_reading["valid"]:
        print(
            f'{gauge_reading["type"]} | Angle: {gauge_reading["angle"]:.1f} deg'
        )

        if gauge_reading["measurement"] is not None:
            print(
                f'Measurement: {gauge_reading["measurement"]:.2f}'
            )

    else:
        print(
            f'{gauge_reading["type"]} detected, but centre/tip could not be determined'
        )

    # Valve detections
    for valve in result["valves"]:
        print(
            "Valve:",
            valve["state"],
            valve["centre"],
        )

    # Camera position relative to each detected marker
    for pose in marker_poses:
        x, y, z = pose.camera_position_m
        print(
            f"ArUco ID {pose.marker_id}: camera "
            f"X {x:+.3f} Y {y:+.3f} Z {z:+.3f} m"
        )
