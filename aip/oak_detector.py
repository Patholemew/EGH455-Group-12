from pathlib import Path

import cv2
import depthai as dai


FALLBACK_LABELS = [
    "ArUco",
    "Blue Gauge",
    "Closed Valve",
    "Gauge Centre",
    "Needle Tip",
    "Open Valve",
    "Plain Gauge",
]


def bbox_centre(bbox):
    """Return centre point (x, y) of a bounding box."""
    x1, y1, x2, y2 = bbox

    return (
        (x1 + x2) / 2.0,
        (y1 + y2) / 2.0,
    )


def point_in_bbox(point, bbox):
    """Check whether a point lies inside a bounding box."""
    x, y = point
    x1, y1, x2, y2 = bbox

    return (
        x1 <= x <= x2
        and y1 <= y <= y2
    )


def bbox_area(bbox):
    """Return bounding-box area."""
    x1, y1, x2, y2 = bbox

    return max(0, x2 - x1) * max(0, y2 - y1)


class OakDetector:
    """
    OAK-D Lite YOLO detector.

    Handles:
    - Blue / Plain gauges
    - Gauge centres
    - Needle tips
    - Open / Closed valves
    - ArUco detections

    Returns both:
    - plain frame
    - annotated frame
    """

    def __init__(
        self,
        model_path,
        confidence=0.40,
        camera_fps=30.0,
    ):

        model_path = Path(model_path).resolve()

        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found: {model_path}"
            )

        # -------------------------------------------------------------
        # Pipeline
        # -------------------------------------------------------------

        self.pipeline = dai.Pipeline()

        archive = dai.NNArchive(
            str(model_path)
        )

        self.input_size = archive.getInputSize()

        self.width = self.input_size[0]
        self.height = self.input_size[1]

        # -------------------------------------------------------------
        # Camera
        # -------------------------------------------------------------

        camera = (
            self.pipeline
            .create(dai.node.Camera)
            .build(dai.CameraBoardSocket.CAM_A)
        )

        camera_output = camera.requestOutput(
            size=self.input_size,
            type=dai.ImgFrame.Type.BGR888p,
            resizeMode=dai.ImgResizeMode.LETTERBOX,
            fps=camera_fps,
        )

        # -------------------------------------------------------------
        # Neural network
        # -------------------------------------------------------------

        self.network = (
            self.pipeline
            .create(dai.node.DetectionNetwork)
            .build(
                camera_output,
                archive,
            )
        )

        self.network.setConfidenceThreshold(
            confidence
        )

        # Try to improve RVC2 throughput.
        self.network.setNumInferenceThreads(2)

        self.network.input.setBlocking(False)

        # -------------------------------------------------------------
        # Labels
        # -------------------------------------------------------------

        archive_labels = self.network.getClasses()

        if archive_labels:
            self.labels = list(archive_labels)
        else:
            self.labels = FALLBACK_LABELS

        # -------------------------------------------------------------
        # Outputs
        # -------------------------------------------------------------

        # Exact image used for YOLO.
        self.frame_queue = (
            self.network
            .passthrough
            .createOutputQueue()
        )

        # Parsed YOLO detections.
        self.detection_queue = (
            self.network
            .out
            .createOutputQueue()
        )

        self.pipeline.start()

    # =================================================================
    # Detection conversion
    # =================================================================

    def _get_label(self, label_id):

        if 0 <= label_id < len(self.labels):
            return self.labels[label_id]

        return f"class_{label_id}"

    def _convert_detection(self, detection):
        """
        Convert DepthAI normalised detection into pixel coordinates.
        """

        x1 = int(
            max(0, min(1, detection.xmin))
            * self.width
        )

        y1 = int(
            max(0, min(1, detection.ymin))
            * self.height
        )

        x2 = int(
            max(0, min(1, detection.xmax))
            * self.width
        )

        y2 = int(
            max(0, min(1, detection.ymax))
            * self.height
        )

        bbox = (
            x1,
            y1,
            x2,
            y2,
        )

        return {
            "label": self._get_label(
                detection.label
            ),
            "confidence": float(
                detection.confidence
            ),
            "bbox": bbox,
            "centre": bbox_centre(bbox),
        }

    # =================================================================
    # Gauge association
    # =================================================================

    def _associate_gauges(
        self,
        gauge_detections,
        centre_detections,
        tip_detections,
    ):
        """
        Associate Gauge Centre and Needle Tip detections with
        the gauge bounding box that contains them.
        """

        gauges = []

        # -------------------------------------------------------------
        # Create basic gauge entries
        # -------------------------------------------------------------

        for detection in gauge_detections:

            gauges.append({
                "type": detection["label"],
                "bbox": detection["bbox"],
                "confidence": detection["confidence"],
                "centre": None,
                "centre_confidence": None,
                "needle_tip": None,
                "needle_tip_confidence": None,
            })

        # -------------------------------------------------------------
        # Associate gauge centre detections
        # -------------------------------------------------------------

        for detection in centre_detections:

            point = detection["centre"]

            possible_gauges = [
                gauge
                for gauge in gauges
                if point_in_bbox(
                    point,
                    gauge["bbox"],
                )
            ]

            if possible_gauges:

                # If boxes overlap, use the smallest containing gauge.
                gauge = min(
                    possible_gauges,
                    key=lambda g: bbox_area(
                        g["bbox"]
                    ),
                )

                # Keep highest confidence centre.
                if (
                    gauge["centre_confidence"] is None
                    or detection["confidence"]
                    > gauge["centre_confidence"]
                ):
                    gauge["centre"] = point

                    gauge["centre_confidence"] = (
                        detection["confidence"]
                    )

        # -------------------------------------------------------------
        # Associate needle tip detections
        # -------------------------------------------------------------

        for detection in tip_detections:

            point = detection["centre"]

            possible_gauges = [
                gauge
                for gauge in gauges
                if point_in_bbox(
                    point,
                    gauge["bbox"],
                )
            ]

            if possible_gauges:

                gauge = min(
                    possible_gauges,
                    key=lambda g: bbox_area(
                        g["bbox"]
                    ),
                )

                # Keep highest confidence tip.
                if (
                    gauge["needle_tip_confidence"]
                    is None
                    or detection["confidence"]
                    > gauge["needle_tip_confidence"]
                ):
                    gauge["needle_tip"] = point

                    gauge["needle_tip_confidence"] = (
                        detection["confidence"]
                    )

        return gauges

    # =================================================================
    # Annotation
    # =================================================================

    def _draw_detection(
        self,
        frame,
        detection,
    ):

        x1, y1, x2, y2 = detection["bbox"]

        label = detection["label"]

        confidence = detection["confidence"]

        text = (
            f"{label} "
            f"{confidence:.2f}"
        )

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2,
        )

        cv2.putText(
            frame,
            text,
            (x1, max(y1 - 5, 15)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

        # Mark bounding-box centre for important point classes.
        if label in (
            "Gauge Centre",
            "Needle Tip",
        ):

            x, y = detection["centre"]

            cv2.circle(
                frame,
                (int(x), int(y)),
                4,
                (0, 0, 255),
                -1,
            )

    # =================================================================
    # Public interface
    # =================================================================

    def read(self):
        """
        Wait for next YOLO inference and return processed result.
        """

        frame_message = self.frame_queue.get()

        detection_message = (
            self.detection_queue.get()
        )

        # This stays completely untouched.
        frame = frame_message.getCvFrame()

        # All annotations go onto a copy.
        annotated_frame = frame.copy()

        detections = [
            self._convert_detection(d)
            for d in detection_message.detections
        ]

        # -------------------------------------------------------------
        # Split detections by type
        # -------------------------------------------------------------

        gauge_detections = [
            d for d in detections
            if d["label"] in (
                "Blue Gauge",
                "Plain Gauge",
            )
        ]

        # -------------------------------------------------------------
        # Only one real gauge can be present.
        # If YOLO produces multiple gauge detections, keep the largest.
        # -------------------------------------------------------------

        if gauge_detections:

            largest_gauge = max(
                gauge_detections,
                key=lambda d: bbox_area(d["bbox"])
            )

            gauge_detections = [largest_gauge]
            

        centre_detections = [
            d for d in detections
            if d["label"] == "Gauge Centre"
        ]

        tip_detections = [
            d for d in detections
            if d["label"] == "Needle Tip"
        ]

        valve_detections = [
            d for d in detections
            if d["label"] in (
                "Open Valve",
                "Closed Valve",
            )
        ]

        aruco_detections = [
            d for d in detections
            if d["label"] == "ArUco"
        ]

        # -------------------------------------------------------------
        # Gauge validation / association
        # -------------------------------------------------------------

        gauges = self._associate_gauges(
            gauge_detections,
            centre_detections,
            tip_detections,
        )

        # -------------------------------------------------------------
        # Simplify valve output
        # -------------------------------------------------------------

        valves = [
            {
                "state": d["label"],
                "centre": d["centre"],
                "bbox": d["bbox"],
                "confidence": d["confidence"],
            }
            for d in valve_detections
        ]

        # -------------------------------------------------------------
        # Simplify ArUco output
        # -------------------------------------------------------------

        arucos = [
            {
                "centre": d["centre"],
                "bbox": d["bbox"],
                "confidence": d["confidence"],
            }
            for d in aruco_detections
        ]

        # -------------------------------------------------------------
        # Annotated image
        # -------------------------------------------------------------

        for detection in detections:

            self._draw_detection(
                annotated_frame,
                detection,
            )

        # -------------------------------------------------------------
        # Final result
        # -------------------------------------------------------------

        return {
            "frame": frame,

            "annotated_frame":
                annotated_frame,

            "gauges": gauges,

            "valves": valves,

            "arucos": arucos,
        }

    def close(self):

        if self.pipeline.isRunning():
            self.pipeline.stop()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.close()