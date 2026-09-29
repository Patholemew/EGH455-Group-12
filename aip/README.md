# AIP Subsystem

Run the subsystem entry point from the repository root:

```bash
python3 aip/aip_main.py
```

`aip_main.py` captures frames from the OAK-D Lite using `OakDetector`, reads
gauges and valves, and displays ArUco outlines and camera pose estimates.
Requires a connected camera, DepthAI v3, OpenCV (`cv2`)
with GUI support, `gpiozero`, and a graphical desktop session. The drill servo
must be connected to BCM GPIO 12.

Set `DRILL_THRESHOLD` in `aip_main.py` to the required gauge measurement. A valid
measurement crossing above the threshold starts one drill-and-return cycle while
camera processing continues. The trigger rearms only after a valid measurement
returns to or below the threshold. Missing and invalid gauge readings do not
trigger or rearm drilling, and overlapping cycles are prevented.

Press **Q** in the frame window, or **Ctrl+C** in the terminal, to
stop capture and close the display.

`aruco.py` detects markers and overlays their outlines and IDs in the live
display. It defaults to `cv2.aruco.DICT_5X5_50`; change `ARUCO_DICTIONARY` in
`aruco.py` to match your printed markers. It requires OpenCV with
`cv2.aruco.ArucoDetector` support (available in the project's OpenCV 4.13).
The `detect_aruco(frame)` function returns `(corners, ids)` for other processing
code, with `ids=None` when no markers are found. The input frame is preserved.
`draw_aruco(frame, corners, ids)` returns an annotated copy. `aip_main.py` handles
pose estimation, the window, quit keys, and window cleanup. Camera positions
are also printed alongside gauge and valve results when `PRINT_RESULTS` is enabled.

Camera position estimation uses `config/camera_intrinsics.yaml` and a **200 mm**
marker side length (outer black square, excluding the white margin). Override
the size for other markers with `--marker-size-mm 150`. All markers in a frame
must have the configured physical size.

The display shows each ID and the camera position in metres relative to that
marker's centre: +X points right, +Y up, and +Z out of the printed face, with
the marker viewed upright. Drawn axes are red X, green Y, and blue Z. Each
marker defines its own coordinate frame; these are not global coordinates.

`PoseEstimator.estimate(frame, corners, ids)` returns `MarkerPose` entries with
`marker_id` and `camera_position_m` (X, Y, Z). It also retains the marker-to-camera
`rvec` and `tvec` used to draw axes. Camera position is computed by inverting
that transform: `-R.T @ tvec`. Missing markers produce no entry; old positions
are not retained. Intrinsics are adjusted from the calibration's 1280 x 720
resolution to the detector's letterboxed frame dimensions.

This is a per-frame estimate. Small or nearly face-on markers can give noisy
or ambiguous poses; verify distances with the physical setup before using
them for control. Run `python3 aip/get_camera_intrinsics.py` with the camera
connected to refresh the YAML calibration.
