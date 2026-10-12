import cv2
import depthai as dai


DISPLAY_SCALE = 0.35
FPS = 10


def centred_square(width, height, zoom):
    """
    Return coordinates for a centred square crop.

    zoom = 1 -> largest square possible
    zoom = 2 -> half width/height of baseline square
    zoom = 3 -> one-third width/height
    """
    base_size = min(width, height)
    crop_size = int(base_size / zoom)

    x1 = (width - crop_size) // 2
    y1 = (height - crop_size) // 2

    x2 = x1 + crop_size
    y2 = y1 + crop_size

    return x1, y1, x2, y2


with dai.Pipeline() as pipeline:

    # RGB camera
    camera = pipeline.create(dai.node.Camera)
    camera.build(dai.CameraBoardSocket.CAM_A)

    # Request full-resolution RGB output
    rgb_output = camera.requestFullResolutionOutput(
        type=dai.ImgFrame.Type.BGR888p,
        fps=FPS,
    )

    queue = rgb_output.createOutputQueue()

    pipeline.start()

    print("Full-resolution crop test")
    print("White = square baseline")
    print("Green = 2x crop")
    print("Red   = 3x crop")
    print()
    print("Press S to save a full-resolution image")
    print("Press Q to quit")

    first_frame = True

    while pipeline.isRunning():

        img_frame = queue.get()
        frame = img_frame.getCvFrame()

        height, width = frame.shape[:2]

        if first_frame:
            print(f"Camera frame: {width} x {height}")

            for zoom in [1, 2, 3]:
                x1, y1, x2, y2 = centred_square(width, height, zoom)
                print(
                    f"{zoom}x crop: "
                    f"{x2 - x1} x {y2 - y1} "
                    f"from ({x1}, {y1}) to ({x2}, {y2})"
                )

            first_frame = False

        display = frame.copy()

        # -------------------------------------------------
        # 1x square baseline
        # -------------------------------------------------
        x1, y1, x2, y2 = centred_square(width, height, 1)

        cv2.rectangle(
            display,
            (x1, y1),
            (x2, y2),
            (255, 255, 255),
            10,
        )

        cv2.putText(
            display,
            "Square baseline",
            (x1 + 20, y1 + 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            (255, 255, 255),
            5,
        )

        # -------------------------------------------------
        # 2x crop
        # -------------------------------------------------
        x1_2, y1_2, x2_2, y2_2 = centred_square(width, height, 2)

        cv2.rectangle(
            display,
            (x1_2, y1_2),
            (x2_2, y2_2),
            (0, 255, 0),
            10,
        )

        cv2.putText(
            display,
            "2x",
            (x1_2 + 20, y1_2 + 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            (0, 255, 0),
            5,
        )

        # -------------------------------------------------
        # 3x crop
        # -------------------------------------------------
        x1_3, y1_3, x2_3, y2_3 = centred_square(width, height, 3)

        cv2.rectangle(
            display,
            (x1_3, y1_3),
            (x2_3, y2_3),
            (0, 0, 255),
            10,
        )

        cv2.putText(
            display,
            "3x",
            (x1_3 + 20, y1_3 + 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            (0, 0, 255),
            5,
        )

        # -------------------------------------------------
        # Resize ONLY for display
        # The actual frame remains full resolution.
        # -------------------------------------------------
        display_small = cv2.resize(
            display,
            None,
            fx=DISPLAY_SCALE,
            fy=DISPLAY_SCALE,
        )

        cv2.imshow("Crop FOV Test", display_small)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        elif key == ord("s"):
            cv2.imwrite("crop_test_full_resolution.jpg", display)
            print("Saved crop_test_full_resolution.jpg")

    pipeline.stop()

cv2.destroyAllWindows()