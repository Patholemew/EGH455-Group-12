"""Entry point for the AIP subsystem."""

import argparse
from pathlib import Path
import time

import cv2

from aruco import detect_aruco, draw_aruco
from oak_detector import OakDetector
from gauge_reader import read_gauge
from pose import PoseEstimator
from wvi_output import prepare_wvi_output


MODEL = (
    Path(__file__).resolve().parent
    / "models"
    / "best_py312_14-09_1828.rvc2.tar.xz"
)

CONFIDENCE = 0.40
SHOW_DISPLAY = True
PRINT_RESULTS = True


def process_gauge(gauges):
    """Read the first detected gauge.

    Returns
    -------
    dict | None
        Gauge reading dictionary, or None if no gauge is detected.
    """
    if not gauges:
        return None

    return read_gauge(gauges[0])


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


def main(argv=None):
    """Run the AIP subsystem."""

    # Command line parser to edit marker size and other parameters. The default marker size is 200 mm.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--marker-size-mm",
        type=float,
        default=200.0,
        help="Marker side length excluding the white margin, in mm (default: 200)",
    )
    args = parser.parse_args(argv)
    pose_estimator = PoseEstimator(args.marker_size_mm / 1000.0)

    with OakDetector(
        MODEL,
        confidence=CONFIDENCE,
    ) as detector:

        frame_count = 0
        fps_start = time.monotonic()

        try:
            while True:

                # ---------------------------------------------------------
                # Run object detection
                # ---------------------------------------------------------

                result = detector.read()

                # Raw frame for other AIP algorithms
                frame = result["frame"]

                # Annotated frame for display
                annotated_frame = result["annotated_frame"]

                # ---------------------------------------------------------
                # Gauge processing
                # ---------------------------------------------------------

                gauge_reading = process_gauge(
                    result["gauges"]
                )

                # ---------------------------------------------------------
                # ArUco detection
                # ---------------------------------------------------------

                # Detect ArUco markers
                aruco_corners, aruco_ids = detect_aruco(frame)
                
                marker_poses = pose_estimator.estimate(
                    frame, aruco_corners, aruco_ids,
                )

                # Draw ArUco markers on the annotated frame
                annotated_frame = draw_aruco(
                    annotated_frame,
                    aruco_corners,
                    aruco_ids,
                )
                annotated_frame = pose_estimator.draw(
                    annotated_frame, marker_poses,
                )

                # ---------------------------------------------------------
                # Output / debugging
                # ---------------------------------------------------------

                if PRINT_RESULTS:
                    print_results(
                        result,
                        gauge_reading,
                        marker_poses,
                    )

                # ---------------------------------------------------------
                # FPS
                # ---------------------------------------------------------

                frame_count += 1
                elapsed = time.monotonic() - fps_start

                if elapsed >= 1.0:
                    if PRINT_RESULTS:
                        print(
                            f"FPS: "
                            f"{frame_count / elapsed:.1f}"
                        )

                    frame_count = 0
                    fps_start = time.monotonic()
                    
                # ---------------------------------------------------------
                # Prepare output for WVI
                # ---------------------------------------------------------

                # Pack all AIP output into a dictionary and encode the annotated frame as JPEG bytes for WVI. The dictionary includes the timestamp, valve states, gauge reading, and camera positions relative to detected markers.
                aip_data, aip_image = prepare_wvi_output(
                    result,
                    gauge_reading,
                    marker_poses,
                    annotated_frame,
                )

                # Temporary placeholders until WVI communication exists
                SEND2SERVER = aip_data
                IMAGE2SERVER = aip_image

                # ---------------------------------------------------------
                # Display
                # ---------------------------------------------------------

                if SHOW_DISPLAY:
                    cv2.imshow(
                        "OAK-D detections",
                        annotated_frame,
                    )

                    if (
                        cv2.waitKey(1) & 0xFF
                        == ord("q")
                    ):
                        break

        except KeyboardInterrupt:
            pass

        finally:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
