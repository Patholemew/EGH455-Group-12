from pathlib import Path
import time

import cv2

from oak_detector import OakDetector
from gauge_reader import read_gauge


MODEL = (
    Path(__file__).resolve().parent
    / "models"
    / "best_py312_12-09_1706.rvc2.tar.xz"
)


with OakDetector(
    MODEL,
    confidence=0.40,
) as detector:

    count = 0
    start = time.monotonic()

    try:

        while True:

            result = detector.read()

            # -------------------------------------------------------------
            # Gauge reading
            # -------------------------------------------------------------

            if result["gauges"]:

                gauge = result["gauges"][0]

                reading = read_gauge(gauge)

                if reading["valid"]:

                    print(
                        f'{reading["type"]} | '
                        f'Angle: {reading["angle"]:.1f} deg'
                    )

                    # Measurement will be None until you add your
                    # angle-to-measurement calibration function.
                    if reading["measurement"] is not None:
                        print(
                            f'Measurement: '
                            f'{reading["measurement"]:.2f}'
                        )

                else:
                    print(
                        f'{gauge["type"]} detected, '
                        f'but centre/tip could not be determined'
                    )

            else:

                print("No reliable gauge detected")

            # ---------------------------------------------
            # Plain frame for teammate's OpenCV ArUco code
            # ---------------------------------------------

            plain_frame = result["frame"]

            # Example later:
            #
            # aruco_pose =
            #     detect_aruco(plain_frame)

            # ---------------------------------------------
            # Gauge results
            # ---------------------------------------------

            for gauge in result["gauges"]:

                print(
                    "Gauge:",
                    gauge["type"],
                )

                print(
                    "  Centre:",
                    gauge["centre"],
                )

                print(
                    "  Needle tip:",
                    gauge["needle_tip"],
                )

                if (
                    gauge["centre"] is not None
                    and
                    gauge["needle_tip"] is not None
                ):
                    print(
                        "  Valid gauge reading"
                    )

            # ---------------------------------------------
            # Valve results
            # ---------------------------------------------

            for valve in result["valves"]:

                print(
                    "Valve:",
                    valve["state"],
                    valve["centre"],
                )

            # ---------------------------------------------
            # YOLO ArUco results
            # ---------------------------------------------

            for aruco in result["arucos"]:

                print(
                    "ArUco:",
                    aruco["centre"],
                )

            # ---------------------------------------------
            # FPS
            # ---------------------------------------------

            count += 1

            elapsed = (
                time.monotonic()
                - start
            )

            if elapsed >= 1.0:

                print(
                    f"FPS: "
                    f"{count / elapsed:.1f}"
                )

                count = 0
                start = time.monotonic()

            # ---------------------------------------------
            # Annotated output
            # ---------------------------------------------

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

cv2.destroyAllWindows()