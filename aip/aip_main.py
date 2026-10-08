"""Entry point for the AIP subsystem."""

import argparse
from pathlib import Path
import sys
from threading import Thread
import time

import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aruco import detect_aruco, draw_aruco
from de.de_main import main as run_drill
from oak_detector import OakDetector
from gauge_reader import process_gauge
from pose import PoseEstimator
from output import print_results
from wvi_output import prepare_wvi_output
from datetime import datetime, timezone

# Load Object Detection Model
MODEL = (
    Path(__file__).resolve().parent
    / "models"
    / "best_04-10_epoch194.rvc2.tar.xz"
)

# ----------------Set parameters ------------------------------

CONFIDENCE = 0.15 # Minimum confidence for object detection
DRILL_THRESHOLD = 2.0 # Gauge measurement below which drilling starts
SHOW_DISPLAY = True # Whether to show the annotated frame in a window. Set to False for headless operation.
PRINT_RESULTS = True # Whether to print detection results to the console. Set to False for headless operation.

#---------------------------------------------------------

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

    # Open OAK-D detector model and run the main loop. The detector is automatically closed when the context manager exits.
    with OakDetector(
        MODEL,
        confidence=CONFIDENCE,
    ) as detector:

        frame_count = 0
        fps_start = time.monotonic()
        drill_thread = None
        drill_trigger_armed = True

        try:
            while True:

                # ---------------------------------------------------------
                # Run object detection
                # ---------------------------------------------------------
                
                # Capture a frame from the OAK-D and run object detection. The result is a dictionary containing the raw frame, annotated frame, and detected gauges.
                result = detector.read()

                # Capture the current timestamp in ISO 8601 format with UTC timezone. This timestamp is used for WVI output.
                frame_timestamp = datetime.now(timezone.utc).isoformat()


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

                #---------------------------------------------------------
                # Drill trigger logic
                #---------------------------------------------------------

                measurement = None
                if (
                    gauge_reading is not None
                    and gauge_reading["valid"]
                ):
                    measurement = gauge_reading["measurement"]

                if measurement is not None:
                    if measurement <= DRILL_THRESHOLD:
                        drill_trigger_armed = True
                    elif drill_trigger_armed:
                        if (
                            drill_thread is None
                            or not drill_thread.is_alive()
                        ):
                            drill_thread = Thread(
                                target=run_drill,
                                name="drill-cycle",
                            )
                            print("Starting drill cycle...")
                            drill_thread.start()

                        drill_trigger_armed = False

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
                    frame_timestamp,
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

                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

        except KeyboardInterrupt:
            pass

        finally:
            # Clean up resources and close the OAK-D detector.
            # If a drill cycle is running, wait for it to finish before exiting.
            if drill_thread is not None:
                drill_thread.join()

            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
