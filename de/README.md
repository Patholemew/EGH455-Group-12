# DE Subsystem

Install the Raspberry Pi GPIO packages, then allow the project virtual
environment to use system packages. Run from the repository root:

```bash
sudo apt install python3-gpiozero python3-lgpio
python3 -m venv --system-site-packages .venv
```

Run the subsystem with that same environment:

```bash
.venv/bin/python de/de_main.py
```

Alternatively, run `/usr/bin/python3 de/de_main.py` using system Python.
In an editor, select `.venv/bin/python` as the interpreter. An isolated virtual
environment cannot see packages installed by `apt` unless system site packages
are enabled as above.

`de_main.py` controls a servo connected to BCM GPIO 12. It runs the servo in the
drilling direction for 10 seconds, pauses for 0.5 seconds, and runs it in the
return direction for 10 seconds. The servo is detached and closed when the run
finishes or is interrupted.

Running this entry point actuates the connected servo.

## Existing Scripts

- `tests/servo_test.py`: moves a servo through minimum, midpoint, and maximum
  positions for six cycles. Requires `gpiozero` and a servo connected to BCM
  GPIO 12. Running this script actuates the servo.
