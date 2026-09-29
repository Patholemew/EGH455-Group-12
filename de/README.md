# DE Subsystem

Run the subsystem entry point from the repository root:

```bash
python3 de/de_main.py
```

Install the GPIO dependency on the Raspberry Pi if needed:

```bash
sudo apt install python3-gpiozero
```

`de_main.py` controls a servo connected to BCM GPIO 12. It runs the servo in the
drilling direction for 10 seconds, pauses for 0.5 seconds, and runs it in the
return direction for 10 seconds. The servo is detached and closed when the run
finishes or is interrupted.

Running this entry point actuates the connected servo.

## Existing Scripts

- `tests/servo_test.py`: moves a servo through minimum, midpoint, and maximum
  positions for six cycles. Requires `gpiozero` and a servo connected to BCM
  GPIO 12. Running this script actuates the servo.
