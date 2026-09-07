# AIP Subsystem

Run the subsystem entry point from the repository root:

```bash
python3 aip/aip_main.py
```

`aip_main.py` captures frames from the OAK-D Lite using `camera.py` and displays
them through `aruco.py`. Requires a connected camera, DepthAI v3, OpenCV (`cv2`)
with GUI support, and a graphical desktop session.

Press **Q** or **Escape** in the frame window, or **Ctrl+C** in the terminal, to
stop capture and close the display.

`aruco.py` currently displays the camera frames; marker detection is not yet
implemented.
