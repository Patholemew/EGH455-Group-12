# AIP Subsystem

The Autonomous Inspection Payload (AIP) uses an OAK-D Lite to detect gauges
and valves, read an analogue gauge, detect ArUco markers, and estimate the
camera position relative to each marker. It produces structured results and an
annotated JPEG frame for future integration with WVI.

## Running AIP

Run the entry point from the repository root:

```bash
python3 aip/aip_main.py
```

`aip_main.py` captures frames from the OAK-D Lite using `OakDetector`, reads
gauges and valves, and displays ArUco outlines and camera pose estimates.
Requires a connected camera, DepthAI v3, OpenCV (`cv2`)
with GUI support for the optional desktop preview, and `gpiozero`. The drill servo
must be connected to BCM GPIO 12.

The desktop preview is enabled only when `DISPLAY` is set. The systemd service
runs without a preview window and continues publishing frames to the website.

Set `DRILL_THRESHOLD` in `aip_main.py` to the required gauge measurement. A valid
measurement crossing above the threshold starts one drill-and-return cycle while
camera processing continues. The trigger rearms only after a valid measurement
returns to or below the threshold. Missing and invalid gauge readings do not
trigger or rearm drilling, and overlapping cycles are prevented.

- an OAK-D Lite connected to the host;
- DepthAI v3;
- NumPy; and
- OpenCV with `cv2.aruco.ArucoDetector` support and, while `SHOW_DISPLAY` is
  enabled, GUI support and a graphical desktop session.

Press lowercase **q** in the display window, or **Ctrl+C** in the terminal, to
stop capture and close the display.

The main runtime settings are constants near the top of `aip_main.py`:

| Setting | Current value | Purpose |
| --- | --- | --- |
| `MODEL` | `aip/models/best_py312_14-09_1828.rvc2.tar.xz` | DepthAI neural-network archive |
| `CONFIDENCE` | `0.40` | Minimum object-detection confidence |
| `SHOW_DISPLAY` | Whether `DISPLAY` is set | Show the annotated OpenCV window in desktop sessions |
| `PRINT_RESULTS` | `True` | Print detections and measured FPS |

`OakDetector` requests a letterboxed BGR camera stream at the model's input
resolution and 30 FPS. It uses the labels embedded in the model archive, or
the fallback labels in `oak_detector.py` when the archive has none.

## Object detection and gauge reading

The detector recognises `Blue Gauge`, `Plain Gauge`, `Gauge Centre`, `Needle`, `Open Valve`, and `Closed Valve`. Its YOLO `ArUco` class is ignored
because OpenCV performs marker detection separately.

Only one physical gauge is expected. If YOLO returns multiple gauge boxes, AIP
keeps the largest and associates the highest-confidence centre and needle
detections contained within it. `process_gauge()` then reads that gauge. The
reading is invalid when either point is missing.

Gauge angles use this convention:

| Needle direction | Angle |
| --- | ---: |
| Bottom | 0 degrees |
| Left | 90 degrees |
| Top | 180 degrees |
| Right | 270 degrees |

`gauge_reader.py` converts the angle to a measurement using separate linear
calibrations for `Blue Gauge` and `Plain Gauge`. The result has no unit encoded
in the current data structure. These calibration equations should be verified
against the physical gauges before the values are used operationally.

Every detected valve is retained with its model label, bounding-box centre,
bounding box, and confidence. The WVI output uses only its label and centre.

## ArUco detection and pose

`aruco.py` uses `cv2.aruco.DICT_5X5_100`. `ARUCO_DICTIONARY` must match the
dictionary used to print the physical markers. `detect_aruco(frame)` returns
`(corners, ids)`, with `ids=None` when no markers are found, without modifying
the input frame. `draw_aruco(frame, corners, ids)` returns an annotated copy.

Camera position estimation uses `config/camera_intrinsics.yaml` and a default
marker side length of **200 mm**, measured across the outer black square and
excluding the white margin. If you want to override the marker size (e.g. to 150mm) when starting AIP, run:

```bash
python3 aip/aip_main.py --marker-size-mm 150
```

All markers visible in a frame must have the configured physical size. The
argument must be a positive, finite number.

The display shows each marker ID and the camera position in metres relative to
that marker's centre. With the marker viewed upright, +X points right, +Y
points up, and +Z points out of the printed face. Drawn axes are red X, green
Y, and blue Z. Each marker defines an independent coordinate frame; these are
not global coordinates.

`PoseEstimator.estimate(frame, corners, ids)` returns one `MarkerPose` for each
successfully solved marker. Each entry contains `marker_id`,
`camera_position_m`, and the marker-to-camera `rvec` and `tvec` used to draw
the axes. Camera position is calculated by inverting that transform:
`-R.T @ tvec`. Failed or non-finite pose solutions are omitted, and positions
from previous frames are not retained.

The calibration must match AIP's camera crop and detector resolution. The
current pipeline takes a 1024 x 1024 camera output, applies the configured
crop/zoom, and resizes it to the model's 640 x 640 input. Refresh the
calibration from the connected camera whenever those settings change:

```bash
python3 aip/get_camera_intrinsics.py
```

This overwrites `config/camera_intrinsics.yaml` with CAM_A's intrinsic matrix
and distortion coefficients. Pose is a per-frame estimate; small or nearly
face-on markers can produce noisy or ambiguous results, so verify estimated
distances with the physical setup before using them for control.

## WVI output

For every camera frame, `aip_main.py` calls `prepare_wvi_output()` from
`wvi_output.py`. It returns two values:

| Value | Python type | Contents |
| --- | --- | --- |
| `aip_data` | `dict` | Timestamp and the valve, gauge, and ArUco results for the frame |
| `aip_image` | `bytes` or `None` | Annotated frame encoded as JPEG, or `None` if encoding fails |

The metadata dictionary has this structure:

```text
{
    "timestamp": str,                   # ISO 8601 UTC timestamp
    "valves": [
        {
            "state": str,               # "Open Valve" or "Closed Valve"
            "centre_px": (float, float) # (x, y) image coordinates
        }
    ],
    "gauge": None | {
        "type": str,                    # "Blue Gauge" or "Plain Gauge"
        "valid": bool,
        "angle": float | None,          # degrees
        "measurement": float | None
    },
    "aruco": [
        {
            "id": int,
            "camera_position_m": {
                "x": float,
                "y": float,
                "z": float
            }
        }
    ]
}
```

Example metadata after conversion to JSON-compatible values:

```json
{
  "timestamp": "2026-09-18T04:15:30.123456+00:00",
  "valves": [
    {"state": "Open Valve", "centre_px": [612.0, 348.0]}
  ],
  "gauge": {
    "type": "Blue Gauge",
    "valid": true,
    "angle": 225.4,
    "measurement": 6.6
  },
  "aruco": [
    {
      "id": 7,
      "camera_position_m": {"x": 0.12, "y": -0.04, "z": 1.31}
    }
  ]
}
```

An empty `valves` or `aruco` list means none were detected in that frame. If
no gauge is detected, `gauge` is `None` (`null` in JSON). A detected gauge can
instead have `valid: false`, with `angle` and `measurement` set to `None`, when
its centre or needle cannot be determined.

### How it is sent to WVI

The output is currently prepared but not transmitted. In `aip_main.py`,
`aip_data` is assigned to the temporary `SEND2SERVER` placeholder and the JPEG
bytes are assigned to `IMAGE2SERVER`. There is currently no network connection,
serialisation step, or receiving implementation in `wvi/wvi_main.py`.

The future WVI transport must send both outputs as parts of the same frame:

1. Convert `aip_data` to structured metadata such as JSON, including conversion
   of tuples and NumPy scalar values to JSON-compatible values.
2. Send `aip_image` as a binary JPEG payload associated with that metadata.

The network protocol, endpoint, message framing, and retry behaviour have not
yet been defined.
