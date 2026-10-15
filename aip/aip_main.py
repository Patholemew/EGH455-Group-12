"""Entry point for the AIP subsystem."""

import argparse
from pathlib import Path
import sys
from threading import Thread
import time
import os
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
from wvi_client import send_aip_output
from datetime import datetime, timezone

# Load Object Detection Model
MODEL = (
    Path(__file__).resolve().parent
    / "models"
    / "best_15-10_640.rvc2.tar.xz"
)

# ----------------Set parameters ------------------------------

CONFIDENCE = 0.10 # Minimum confidence for object detection
DRILL_THRESHOLD = 2.0 # Gauge measurement below which drilling starts
CAMERA_FPS = 15.0 # Camera frames per second. The OAK-D camera will be set to this FPS, and the AIP will process frames at this rate.
# The systemd service has no X display; opening an OpenCV window there aborts
# the process after its first frame. Keep the preview for desktop sessions.
SHOW_DISPLAY = bool(os.environ.get("DISPLAY"))
PRINT_RESULTS = False # Whether to print detection results to the console. Set to False for headless operation.
SHOW_TIMINGS = False
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
        camera_fps=CAMERA_FPS,
    ) as detector:

        frame_count = 0
        fps_start = time.monotonic()
        drill_thread = None
        drill_trigger_armed = True
        timings_prev = {}

        try:
            while True:
                loop_start = time.perf_counter()

                # ---------------------------------------------------------
                # Run object detection
                # ---------------------------------------------------------
                
                # Get the next completed object-detection result from the continuously running OAK-D pipeline.
                #  The result is a dictionary containing the raw frame, annotated frame, and detected gauges.
                t0 = time.perf_counter()
                result = detector.read()
                t1 = time.perf_counter()
                detector_ms = (t1 - t0) * 1000

                # Capture the current timestamp in ISO 8601 format with UTC timezone. This timestamp is used for WVI output.
                frame_timestamp = datetime.now(timezone.utc).isoformat()


                # Raw frame for other AIP algorithms
                frame = result["frame"]

                # Annotated frame for display
                annotated_frame = result["annotated_frame"]

                # ---------------------------------------------------------
                # Gauge processing
                # ---------------------------------------------------------
                t0 = time.perf_counter()
                gauge_reading = process_gauge(
                    result["gauges"]
                )
                t1 = time.perf_counter()
                gauge_ms = (t1 - t0) * 1000

                #---------------------------------------------------------
                # Drill trigger logic
                #---------------------------------------------------------
                t0 = time.perf_counter()
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
                t1 = time.perf_counter()
                drill_ms = (t1 - t0) * 1000

                # ---------------------------------------------------------
                # ArUco detection
                # ---------------------------------------------------------
                t0 = time.perf_counter()
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

                t1 = time.perf_counter()
                aruco_ms = (t1 - t0) * 1000

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


                if SHOW_TIMINGS and timings_prev:
                    timing_lines = [
                        f"Loop FPS: {timings_prev['fps']:.1f}",
                        f"Detector: {timings_prev['detector']:.1f} ms",
                        f"Gauge: {timings_prev['gauge']:.1f} ms",
                        f"Drill: {timings_prev['drill']:.1f} ms",
                        f"ArUco: {timings_prev['aruco']:.1f} ms",
                        f"WVI prep: {timings_prev['wvi_prep']:.1f} ms",
                        f"WVI send: {timings_prev['wvi_send']:.1f} ms",
                        f"Other: {timings_prev['other']:.1f} ms",
                        f"TOTAL: {timings_prev['total']:.1f} ms",
                    ]

                    y = 55

                    for line in timing_lines:
                        cv2.putText(
                            annotated_frame,
                            line,
                            (10, y),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.45,
                            (255, 255, 255),
                            1,
                            cv2.LINE_AA,
                        )

                        y += 18
                    
                # ---------------------------------------------------------
                # Prepare output for WVI
                # ---------------------------------------------------------
                # Pack all AIP output into a dictionary and encode the annotated frame as JPEG bytes for WVI. The dictionary includes the timestamp, valve states, gauge reading, and camera positions relative to detected markers.
                t0 = time.perf_counter()
                aip_data, aip_image = prepare_wvi_output(
                    result,
                    gauge_reading,
                    marker_poses,
                    frame_timestamp,
                    annotated_frame,
                )

                t1 = time.perf_counter()
                wvi_prep_ms = (t1 - t0) * 1000

                # Temporary placeholders until WVI communication exists
                t0 = time.perf_counter()

                try:
                    send_aip_output(aip_data, aip_image)
                except:
                    print(f"WVI output failure")

                t1 = time.perf_counter()
                wvi_send_ms = (t1 - t0) * 1000

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

                # ---------------------------------------------------------
                # Store timing information for next frame
                # ---------------------------------------------------------
                loop_end = time.perf_counter()
                total_ms = (loop_end - loop_start) * 1000

                measured_ms = (
                    detector_ms
                    + gauge_ms
                    + drill_ms
                    + aruco_ms
                    + wvi_prep_ms
                    + wvi_send_ms
                )

                other_ms = max(0.0, total_ms - measured_ms)

                if total_ms > 0:
                    loop_fps = 1000.0 / total_ms
                else:
                    loop_fps = 0.0

                timings_prev = {
                    "detector": detector_ms,
                    "gauge": gauge_ms,
                    "drill": drill_ms,
                    "aruco": aruco_ms,
                    "wvi_prep": wvi_prep_ms,
                    "wvi_send": wvi_send_ms,
                    "other": other_ms,
                    "total": total_ms,
                    "fps": loop_fps,
                }

        except KeyboardInterrupt:
            pass

        finally:
            # Clean up resources and close the OAK-D detector.
            # If a drill cycle is running, wait for it to finish before exiting.
            if drill_thread is not None:
                drill_thread.join()

            if SHOW_DISPLAY:
                cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
