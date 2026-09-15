"""Entry point for the AIP subsystem."""

from pathlib import Path
import time

import cv2

from gauge_reader import read_gauge
from oak_detector import OakDetector


MODEL = (
    Path(__file__).resolve().parent
    / "models"
    / "best_py312_14-09_1828.rvc2.tar.xz"
)


def main():
    """Run OAK-D detection until Q, Escape, or Ctrl+C is pressed."""
    with OakDetector(MODEL, confidence=0.40) as detector:
        count = 0
        start = time.monotonic()

        try:
            while True:
                result = detector.read()

                if result["gauges"]:
                    gauge = result["gauges"][0]
                    reading = read_gauge(gauge)

                    if reading["valid"]:
                        print(
                            f'{reading["type"]} | '
                            f'Angle: {reading["angle"]:.1f} deg'
                        )

                        if reading["measurement"] is not None:
                            print(f'Measurement: {reading["measurement"]:.2f}')
                    else:
                        print(
                            f'{gauge["type"]} detected, '
                            "but centre/tip could not be determined"
                        )
                else:
                    print("No reliable gauge detected")

                # Unannotated frame for future OpenCV ArUco processing.
                plain_frame = result["frame"]

                for gauge in result["gauges"]:
                    print("Gauge:", gauge["type"])
                    print("  Centre:", gauge["centre"])
                    print("  Needle tip:", gauge["needle_tip"])

                    if (
                        gauge["centre"] is not None
                        and gauge["needle_tip"] is not None
                    ):
                        print("  Valid gauge reading")

                for valve in result["valves"]:
                    print("Valve:", valve["state"], valve["centre"])

                for aruco in result["arucos"]:
                    print("ArUco:", aruco["centre"])

                count += 1
                elapsed = time.monotonic() - start

                if elapsed >= 1.0:
                    print(f"FPS: {count / elapsed:.1f}")
                    count = 0
                    start = time.monotonic()

                cv2.imshow("OAK-D detections", result["annotated_frame"])
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):
                    break

        except KeyboardInterrupt:
            print("Stopping AIP system")
        finally:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
