#!/usr/bin/env python3

"""
Test a custom YOLOv5 model on an OAK-D Lite using DepthAI v3.

The model is a Luxonis RVC2 NNArchive (.tar.xz) produced by HubAI.

Features:
- Loads the local RVC2 model archive.
- Uses the OAK-D Lite RGB camera.
- Runs YOLO inference directly on the OAK-D Lite.
- Uses DepthAI DetectionNetwork so YOLO output is decoded on-device.
- Draws bounding boxes and class names.
- Prints FPS and detection counts.
- Can save annotated video.
- Can optionally display a live OpenCV window.
- Safe to run over SSH because display is OFF by default.

Press Ctrl+C to stop when running over SSH.
If using --display, press Q to stop.
"""

from pathlib import Path
import argparse
import time

import cv2
import depthai as dai


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_MODEL = (
    SCRIPT_DIR
    / "models"
    / "best_8-9-26_2147_py312.rvc2.tar.xz"
)


# ---------------------------------------------------------------------
# Fallback class names
#
# These are the six classes documented in the previous project material.
# Normally the class names should be loaded directly from the NNArchive.
# ---------------------------------------------------------------------

FALLBACK_LABELS = [
    "valve_open",
    "valve_closed",
    "gauge_1",
    "gauge_2",
    "gauge_centre",
    "needle_tip",
]


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------

def clamp(value, minimum, maximum):
    """Clamp a number to a specified range."""
    return max(minimum, min(value, maximum))


def get_label(label_id, labels):
    """
    Convert numeric YOLO class ID into a readable class name.

    If the archive contains a class we don't know about, display class_N
    instead of crashing.
    """
    if 0 <= label_id < len(labels):
        return labels[label_id]

    return f"class_{label_id}"


def draw_detection(frame, detection, labels):
    """Draw one DepthAI detection onto an OpenCV image."""

    height, width = frame.shape[:2]

    # DepthAI bounding boxes are normalised from 0 to 1.
    x1 = int(clamp(detection.xmin, 0.0, 1.0) * width)
    y1 = int(clamp(detection.ymin, 0.0, 1.0) * height)
    x2 = int(clamp(detection.xmax, 0.0, 1.0) * width)
    y2 = int(clamp(detection.ymax, 0.0, 1.0) * height)

    label = get_label(detection.label, labels)

    text = f"{label}: {detection.confidence:.2f}"

    # Bounding box
    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        (255, 255, 255),
        2,
    )

    # Text background
    (text_width, text_height), _ = cv2.getTextSize(
        text,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        1,
    )

    text_y = max(y1 - 5, text_height + 5)

    cv2.rectangle(
        frame,
        (x1, text_y - text_height - 5),
        (x1 + text_width + 4, text_y + 2),
        (0, 0, 0),
        -1,
    )

    # Text
    cv2.putText(
        frame,
        text,
        (x1 + 2, text_y - 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )


def create_video_writer(path, frame, fps):
    """Create an OpenCV VideoWriter after frame dimensions are known."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    height, width = frame.shape[:2]

    if path.suffix.lower() == ".mp4":
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    else:
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")

    writer = cv2.VideoWriter(
        str(path),
        fourcc,
        fps,
        (width, height),
    )

    if not writer.isOpened():
        raise RuntimeError(f"Could not open video file for writing: {path}")

    return writer


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Run custom YOLOv5 model on OAK-D Lite using DepthAI v3."
    )

    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL,
        help="Path to Luxonis RVC2 .tar.xz model archive.",
    )

    parser.add_argument(
        "--confidence",
        type=float,
        default=0.40,
        help="Detection confidence threshold. Default: 0.40",
    )

    parser.add_argument(
        "--fps",
        type=float,
        default=20.0,
        help="Requested RGB camera FPS. Default: 20",
    )

    parser.add_argument(
        "--display",
        action="store_true",
        help="Show live OpenCV window. Do NOT use this over normal SSH.",
    )

    parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Save annotated video, e.g. aip/yolo_output.avi",
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=0,
        help="Automatically stop after N seconds. 0 = run until stopped.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every individual detection.",
    )

    args = parser.parse_args()

    model_path = args.model.resolve()

    # -----------------------------------------------------------------
    # Check model
    # -----------------------------------------------------------------

    if not model_path.exists():
        raise FileNotFoundError(
            f"\nModel not found:\n{model_path}\n"
        )

    print("=" * 60)
    print("OAK-D Lite YOLOv5 test")
    print("=" * 60)

    print(f"DepthAI version: {dai.__version__}")
    print(f"Model: {model_path}")

    # Load the archive generated by Luxonis HubAI.
    archive = dai.NNArchive(str(model_path))

    print(f"Model type: {archive.getModelType()}")

    input_size = archive.getInputSize()

    print(f"Model input size: {input_size}")

    # -----------------------------------------------------------------
    # Build DepthAI pipeline
    # -----------------------------------------------------------------

    with dai.Pipeline() as pipeline:

        print("\nCreating camera...")

        # CAM_A is the colour/RGB camera on the OAK-D Lite.
        camera = pipeline.create(dai.node.Camera).build(
            dai.CameraBoardSocket.CAM_A
        )

        # Request an image matching the neural network input size.
        #
        # LETTERBOX preserves the camera aspect ratio instead of stretching
        # the image. This matches the normal YOLO preprocessing approach.
        camera_output = camera.requestOutput(
            size=input_size,
            type=dai.ImgFrame.Type.BGR888p,
            resize_mode=dai.ImgResizeMode.LETTERBOX,
            fps=args.fps,
        )

        print("Creating YOLO DetectionNetwork...")

        # DetectionNetwork does BOTH:
        #
        # 1. Neural-network inference
        # 2. YOLO output decoding / NMS
        #
        # This means we receive normal bounding boxes instead of having to
        # manually decode the raw (1, 25200, ...) tensor.
        detection_network = (
            pipeline.create(dai.node.DetectionNetwork)
            .build(camera_output, archive)
        )

        detection_network.setConfidenceThreshold(args.confidence)

        # Non-blocking input helps avoid building up stale camera frames.
        detection_network.input.setBlocking(False)

        # Try to get class names directly from the converted model.
        archive_labels = detection_network.getClasses()

        if archive_labels:
            labels = list(archive_labels)

            print("\nClass names loaded from NNArchive:")

            for index, name in enumerate(labels):
                print(f"  {index}: {name}")

        else:
            labels = FALLBACK_LABELS

            print("\nWARNING: Model archive did not provide class names.")
            print("Using fallback class list:")

            for index, name in enumerate(labels):
                print(f"  {index}: {name}")

        # The passthrough output gives us the exact image that was sent
        # into the neural network.
        rgb_queue = (
            detection_network
            .passthrough
            .createOutputQueue()
        )

        # DetectionNetwork.out provides parsed ImgDetections.
        detection_queue = (
            detection_network
            .out
            .createOutputQueue()
        )

        # -----------------------------------------------------------------
        # Start OAK-D Lite
        # -----------------------------------------------------------------

        print("\nStarting pipeline...")

        pipeline.start()

        print("YOLO is running.")

        if args.display:
            print("Press Q in the video window to quit.")
        else:
            print("Press Ctrl+C to quit.")

        if args.save is not None:
            print(f"Saving annotated video to: {args.save}")

        print("=" * 60)

        writer = None

        start_time = time.monotonic()

        fps_start = start_time
        fps_frame_count = 0
        measured_fps = 0.0

        try:

            while pipeline.isRunning():

                # ---------------------------------------------------------
                # Get synchronised NN frame and detections
                # ---------------------------------------------------------

                frame_message = rgb_queue.get()
                detection_message = detection_queue.get()

                frame = frame_message.getCvFrame()

                detections = detection_message.detections

                # ---------------------------------------------------------
                # Draw detections
                # ---------------------------------------------------------

                for detection in detections:

                    draw_detection(
                        frame,
                        detection,
                        labels,
                    )

                    if args.verbose:

                        label = get_label(
                            detection.label,
                            labels,
                        )

                        print(
                            f"{label:<20} "
                            f"confidence={detection.confidence:.3f}"
                        )

                # ---------------------------------------------------------
                # Calculate approximate host-side FPS
                # ---------------------------------------------------------

                fps_frame_count += 1

                current_time = time.monotonic()

                elapsed_fps = current_time - fps_start

                if elapsed_fps >= 1.0:

                    measured_fps = fps_frame_count / elapsed_fps

                    fps_frame_count = 0
                    fps_start = current_time

                    print(
                        f"FPS: {measured_fps:5.1f} | "
                        f"Detections: {len(detections)}"
                    )

                # Show FPS on image.
                cv2.putText(
                    frame,
                    f"FPS: {measured_fps:.1f}",
                    (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

                # ---------------------------------------------------------
                # Save video
                # ---------------------------------------------------------

                if args.save is not None:

                    if writer is None:
                        writer = create_video_writer(
                            args.save,
                            frame,
                            args.fps,
                        )

                    writer.write(frame)

                # ---------------------------------------------------------
                # Optional live display
                # ---------------------------------------------------------

                if args.display:

                    cv2.imshow(
                        "OAK-D Lite - YOLOv5",
                        frame,
                    )

                    key = cv2.waitKey(1) & 0xFF

                    if key == ord("q"):
                        break

                # ---------------------------------------------------------
                # Optional automatic stop
                # ---------------------------------------------------------

                if args.duration > 0:

                    elapsed_total = (
                        time.monotonic()
                        - start_time
                    )

                    if elapsed_total >= args.duration:
                        print("\nRequested duration reached.")
                        break

        except KeyboardInterrupt:
            print("\nCtrl+C received.")

        finally:

            if writer is not None:
                writer.release()

            if args.display:
                cv2.destroyAllWindows()

            print("Stopping pipeline.")

    print("Done.")


if __name__ == "__main__":
    main()