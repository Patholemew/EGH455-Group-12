"""Entry point for the AIP subsystem."""

from pathlib import Path
import time

import cv2

from oak_detector import OakDetector
from gauge_reader import read_gauge


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


def print_results(result, gauge_reading):
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


def main():
    """Run the AIP subsystem."""

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
                # ArUco pose estimation
                # ---------------------------------------------------------

                # Teammate's OpenCV ArUco processing can use:
                #
                # aruco_pose = detect_aruco(frame)

                # ---------------------------------------------------------
                # Output / debugging
                # ---------------------------------------------------------

                if PRINT_RESULTS:
                    print_results(
                        result,
                        gauge_reading,
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
                # Display
                # ---------------------------------------------------------

                if SHOW_DISPLAY:
                    cv2.imshow(
                        "OAK-D detections",
                        result["annotated_frame"],
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