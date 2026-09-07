# DE Subsystem

Run the subsystem entry point from the repository root:

```bash
python3 de/de_main.py
```

`de_main.py` is a scaffold for subsystem startup and coordination. It currently
prints a status message and does not access hardware.

## Existing Scripts

- `tests/servo_test.py`: moves a servo through minimum, midpoint, and maximum
  positions for six cycles. Requires `gpiozero` and a servo connected to BCM
  GPIO 12. Running this script actuates the servo.

Add subsystem startup logic to `main()` in `de_main.py` as it is developed.
