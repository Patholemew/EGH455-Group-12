# AIP Subsystem

Run the subsystem entry point from the repository root:

```bash
python3 aip/aip_main.py
```

`aip_main.py` captures frames from the OAK-D Lite using `camera.py` and displays
them through `display.py` after detection and annotation in `aruco.py`.
Requires a connected camera, DepthAI v3, OpenCV (`cv2`)
with GUI support, and a graphical desktop session.

Press **Q** or **Escape** in the frame window, or **Ctrl+C** in the terminal, to
stop capture and close the display.

`aruco.py` detects markers and overlays their outlines and IDs in the live
display. It defaults to `cv2.aruco.DICT_5X5_50`; change `ARUCO_DICTIONARY` in
`aruco.py` to match your printed markers. It requires OpenCV with
`cv2.aruco.ArucoDetector` support (available in the project's OpenCV 4.13).
The `detect_aruco(frame)` function returns `(corners, ids)` for other processing
code, with `ids=None` when no markers are found. The input frame is preserved.
`draw_aruco(frame, corners, ids)` returns an annotated copy. `display.py` handles
the window, quit keys, and window cleanup; `aip_main.py` coordinates these steps.

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
are not retained. Frames must match the calibration's 1280 x 720 resolution.

This is a per-frame estimate. Small or nearly face-on markers can give noisy
or ambiguous poses; verify distances with the physical setup before using
them for control. Run `python3 aip/get_camera_intrinsics.py` with the camera
connected to refresh the YAML calibration.
