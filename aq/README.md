# AQ Subsystem

Run the subsystem entry point from the repository root:

```bash
python3 aq/aq_main.py
```

`aq_main.py` samples once per second and posts readings to WVI. It samples for
30 seconds after the first successful read before publishing, so startup
artifacts are not stored. The gas heater starts on the first read. Configure
the settling time with `AQ_WARMUP_SECONDS` (seconds, default `30`); even `0`
discards the first sample. This is a startup artifact guard, not a guarantee
that gas readings have fully stabilised after a cold boot. Increase the period
if measurements show a longer settling time. The dashboard shows Waiting or
Stale during this period. CPU temperature compensation uses five recent samples.

Charts leave a break when samples are more than five seconds apart. Existing
bad readings remain stored until explicitly cleaned. Preview specific IDs:

```bash
python3 scripts/clean_air_readings.py --database /var/lib/uav-wvi/wvi.sqlite3 --ids 123 456
```

Use actual IDs verified against restart times and neighbouring readings. Add
`--apply --backup /path/to/new-backup.sqlite3` to remove those rows after making
a full SQLite backup, including committed WAL data. Do not remove readings
solely because they are unusually high or low; actual environmental changes
can produce spikes too. Other database tables are left intact.

## Existing Scripts

- `AQFunctions.py`: contains all the functions, classes and libaries required for `aq_main.py`
  to run properly. The "readings" class self contains all the methods required to
  record and present data to the terminal, but requires some external functions to work.
- `display_ALL.py`: displays camera images, the IP address, and temperature
  readings on an ST7735 LCD. Requires a DepthAI camera, BME280 sensor, ST7735
  display, and the Python packages imported by the script. It uses the DepthAI
  v3 API and Raspberry Pi I2C, SPI, and CPU temperature interfaces.

Before running `display_ALL.py`, stop any other program using the LCD. If the IP
display service is running, stop it with `sudo systemctl stop display_ip.service`.

Both LCD scripts require Pillow for image loading, resizing, fonts, and text
drawing. Install this image dependency into the project environment from the
repository root (the hardware drivers must also be installed):

```bash
.venv/bin/python -m pip install -r aq/requirements-display.txt
```

Pillow provides the `PIL` import; it is a runtime dependency of the LCD scripts.
