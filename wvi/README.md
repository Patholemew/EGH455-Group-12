# WVI Subsystem

Run the subsystem entry point from the repository root:

```bash
python3 wvi/wvi_main.py
```

`wvi_main.py` is a scaffold for subsystem startup and coordination. It currently
prints a status message and does not access hardware. No additional subsystem
scripts or dependencies have been added yet.

Add subsystem startup logic to `main()` in `wvi_main.py` as it is developed.
