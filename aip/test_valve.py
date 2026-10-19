"""Test valve detection and classification performance over a fixed number of frames."""

import csv
import time
from pathlib import Path

import cv2

from oak_detector import OakDetector


# ============================================================
# TEST SETTINGS - CHANGE THESE FOR EACH TEST
# ============================================================

TRUE_STATE = "open"       # Actual valve state: "open" or "closed"
TEST_DISTANCE = 3.0      # Distance from camera to valve, metres
POSITION = "right"       # Viewing position: "centre", "left", or "right"
NUM_FRAMES = 200          # Number of frames to record

SHOW_DISPLAY = False


# Load Object Detection Model
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
# valve_test_0.7m_open_centre.csv

OUTPUT_FILE = (
    Path(__file__).resolve().parent
    / "csv_tests"
    / f"valve_test_{TEST_DISTANCE}m_{TRUE_STATE}_{POSITION}.csv"
)


def normalise_state(state):
    """Convert valve state to 'open' or 'closed' where possible."""

    if state is None:
        return None

    state = str(state).strip().lower()

    # Allows for either:
    #   "open"
    #   "closed"
    #   "Open Valve"
    #   "Closed Valve"

    if "open" in state:
        return "open"

    if "closed" in state:
        return "closed"

    return state


def main():

    true_state = normalise_state(TRUE_STATE)

    if true_state not in ("open", "closed"):
        raise ValueError(
            "TRUE_STATE must be either 'open' or 'closed'."
        )

    # Make sure output directory exists
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("==========================================")
    print("Valve Detection Test")
    print("==========================================")
    print(f"Distance:     {TEST_DISTANCE} m")
    print(f"True state:   {true_state}")
    print(f"Position:     {POSITION}")
    print(f"Frames:       {NUM_FRAMES}")
    print(f"Output file:  {OUTPUT_FILE.name}")
    print("==========================================")
    print("Press Q to stop the test early.")
    print()

    fieldnames = [
        "frame",
        "distance_m",
        "position",
        "true_state",
        "detected",
        "predicted_state",
        "correct",
        "valve_confidence",
    ]

    detected_count = 0
    correct_count = 0
    frames_recorded = 0

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
                # Default values for a failed detection
                # ------------------------------------------------

                detected = False
                predicted_state = None
                correct = False
                valve_confidence = None

                # ------------------------------------------------
                # Process valve detection
                # ------------------------------------------------

                if result["valves"]:

                    # Use highest-confidence valve if more than one
                    # detection is present.
                    valve = max(
                        result["valves"],
                        key=lambda v: v["confidence"],
                    )

                    detected = True

                    predicted_state = normalise_state(
                        valve.get("state")
                    )

                    valve_confidence = valve.get(
                        "confidence"
                    )

                    correct = (
                        predicted_state == true_state
                    )

                # ------------------------------------------------
                # Update counters
                # ------------------------------------------------

                frames_recorded += 1

                if detected:
                    detected_count += 1

                if correct:
                    correct_count += 1

                # ------------------------------------------------
                # Write this frame to CSV
                # ------------------------------------------------

                writer.writerow({
                    "frame": frame_number,
                    "distance_m": TEST_DISTANCE,
                    "position": POSITION,
                    "true_state": true_state,
                    "detected": detected,
                    "predicted_state": predicted_state,
                    "correct": correct,
                    "valve_confidence": valve_confidence,
                })

                # Save immediately in case program is stopped
                csv_file.flush()

                # ------------------------------------------------
                # Console output
                # ------------------------------------------------

                if detected:

                    status = (
                        "CORRECT"
                        if correct
                        else "WRONG"
                    )

                    confidence_text = (
                        f"{valve_confidence:.3f}"
                        if valve_confidence is not None
                        else "N/A"
                    )

                    print(
                        f"Frame {frame_number}/{NUM_FRAMES}: "
                        f"{predicted_state.upper()} "
                        f"({confidence_text}) - "
                        f"{status}"
                    )

                else:

                    print(
                        f"Frame {frame_number}/{NUM_FRAMES}: "
                        f"NO DETECTION"
                    )

                # ------------------------------------------------
                # Display
                # ------------------------------------------------

                if SHOW_DISPLAY:

                    cv2.imshow(
                        "Valve Detection Test",
                        result["annotated_frame"],
                    )

                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        print("\nTest stopped early.")
                        break

            elapsed = time.monotonic() - start_time

    cv2.destroyAllWindows()

    # ============================================================
    # FINAL SUMMARY
    # ============================================================

    if frames_recorded > 0:

        detection_rate = (
            detected_count
            / frames_recorded
            * 100
        )

        overall_accuracy = (
            correct_count
            / frames_recorded
            * 100
        )

    else:

        detection_rate = 0
        overall_accuracy = 0

    if detected_count > 0:

        classification_accuracy = (
            correct_count
            / detected_count
            * 100
        )

    else:

        classification_accuracy = 0

    print()
    print("==========================================")
    print("Test complete")
    print("==========================================")
    print(f"Frames recorded:         {frames_recorded}")
    print(
        f"Valve detected:          "
        f"{detected_count}/{frames_recorded} "
        f"({detection_rate:.1f}%)"
    )
    print(
        f"Correct overall:         "
        f"{correct_count}/{frames_recorded} "
        f"({overall_accuracy:.1f}%)"
    )
    print(
        f"Accuracy when detected:  "
        f"{correct_count}/{detected_count} "
        f"({classification_accuracy:.1f}%)"
        if detected_count > 0
        else "Accuracy when detected:  N/A"
    )
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"Test duration: {elapsed:.1f} s")


if __name__ == "__main__":
    main()