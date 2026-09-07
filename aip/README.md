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
display. It defaults to `cv2.aruco.DICT_4X4_50`; change `ARUCO_DICTIONARY` in
`aruco.py` to match your printed markers. It requires OpenCV with
`cv2.aruco.ArucoDetector` support (available in the project's OpenCV 4.13).
The `detect_aruco(frame)` function returns `(corners, ids)` for other processing
code, with `ids=None` when no markers are found. The input frame is preserved.
`draw_aruco(frame, corners, ids)` returns an annotated copy. `display.py` handles
the window, quit keys, and window cleanup; `aip_main.py` coordinates these steps.
