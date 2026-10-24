"""Test gauge reading performance over a fixed number of frames."""

import csv
import time
from pathlib import Path

import cv2

from oak_detector import OakDetector
from gauge_reader import process_gauge


# ============================================================
# TEST SETTINGS - CHANGE THESE FOR EACH TEST
# ============================================================

TRUE_VALUE = 1.75        # Actual gauge value
TEST_DISTANCE = 0.7     # Distance from camera to gauge, metres
NUM_FRAMES = 200        # Number of frames to record
GAUGE_TYPE = "plain"    # Gauge type: "blue" or "plain"
POSITION = "left"     # Position of camera from gauge: "centre", "left", or "right"

SHOW_DISPLAY = True

# Same model used by aip_main.py
MODEL = (
    Path(__file__).resolve().parent
    / "models"
    / "best_15-10_640.rvc2.tar.xz"
)

# Same minimum NN confidence as aip_main.py
CONFIDENCE = 0.10


# ============================================================
# OUTPUT FILE
# ============================================================

# Example:
OUTPUT_FILE = (
    Path(__file__).resolve().parent / "csv_tests"
    / f"gauge_test_{TEST_DISTANCE}m_{TRUE_VALUE}_{POSITION}_{GAUGE_TYPE}.csv"
)


def main():

    print("==========================================")
    print("Gauge Distance Test")
    print("==========================================")
    print(f"Distance:    {TEST_DISTANCE} m")
    print(f"True value:  {TRUE_VALUE}")
    print(f"Position:    {POSITION}")
    print(f"Gauge type:  {GAUGE_TYPE}")
    print(f"Frames:      {NUM_FRAMES}")
    print(f"Output file: {OUTPUT_FILE.name}")
    print("==========================================")
    print("Press Q to stop the test early.")
    print()

    fieldnames = [
        "frame",
        "distance_m",
        "true_value",
        "position",
        "gauge_type",
        "success",
        "measured_value",
        "gauge_confidence",
        "centre_confidence",
        "needle_confidence",
    ]

    with OakDetector(
        MODEL,
        confidence=CONFIDENCE,
    ) as detector:

        with open(
            OUTPUT_FILE,
            "w",
            newline="",
        ) as csv_file:

            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            start_time = time.monotonic()

            for frame_number in range(1, NUM_FRAMES + 1):

                # ------------------------------------------------
                # Run object detection
                # ------------------------------------------------

                result = detector.read()

                # ------------------------------------------------
                # Process gauge
                # ------------------------------------------------

                gauge_reading = process_gauge(
                    result["gauges"]
                )

                # Default values for a failed frame
                success = False
                measured_value = None

                gauge_confidence = None
                centre_confidence = None
                needle_confidence = None

                # ------------------------------------------------
                # Get raw gauge detection confidence information
                # ------------------------------------------------

                if result["gauges"]:

                    gauge = result["gauges"][0]

                    gauge_confidence = gauge.get(
                        "confidence"
                    )

                    centre_confidence = gauge.get(
                        "centre_confidence"
                    )

                    needle_confidence = gauge.get(
                        "needle_confidence"
                    )

                # ------------------------------------------------
                # Determine whether this frame produced a valid
                # gauge measurement
                # ------------------------------------------------

                if (
                    gauge_reading is not None
                    and gauge_reading["valid"]
                ):
                    measured_value = gauge_reading[
                        "measurement"
                    ]

                    success = True

                # ------------------------------------------------
                # Write this frame to CSV
                # ------------------------------------------------

                writer.writerow({
                    "frame": frame_number,
                    "distance_m": TEST_DISTANCE,
                    "true_value": TRUE_VALUE,
                    "position": POSITION,
                    "gauge_type": GAUGE_TYPE,
                    "success": success,
                    "measured_value": measured_value,
                    "gauge_confidence": gauge_confidence,
                    "centre_confidence": centre_confidence,
                    "needle_confidence": needle_confidence,
                })

                # Save immediately in case the program is stopped
                csv_file.flush()

                # ------------------------------------------------
                # Console output
                # ------------------------------------------------

                if success:
                    print(
                        f"Frame {frame_number}/{NUM_FRAMES}: "
                        f"{measured_value:.2f}"
                    )
                else:
                    print(
                        f"Frame {frame_number}/{NUM_FRAMES}: "
                        f"FAILED"
                    )

                # ------------------------------------------------
                # Display
                # ------------------------------------------------

                if SHOW_DISPLAY:

                    cv2.imshow(
                        "Gauge Distance Test",
                        result["annotated_frame"],
                    )

                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        print("\nTest stopped early.")
                        break

            elapsed = time.monotonic() - start_time

    cv2.destroyAllWindows()

    print()
    print("==========================================")
    print("Test complete")
    print("==========================================")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"Test duration: {elapsed:.1f} s")


if __name__ == "__main__":
    main()