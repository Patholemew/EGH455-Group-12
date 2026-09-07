# AIP Subsystem

Run the subsystem entry point from the repository root:

```bash
python3 aip/aip_main.py
```

`aip_main.py` is a scaffold for subsystem startup and coordination. It currently
prints a status message and does not access hardware.

## Existing Scripts

- `test_cam.py`: captures one camera frame and saves `test_image.jpg` in the
  working directory. Requires a connected DepthAI camera, `depthai`, and OpenCV
  (`cv2`). The script uses the DepthAI v2 API.

Add subsystem startup logic to `main()` in `aip_main.py` as it is developed.
