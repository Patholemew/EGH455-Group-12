# AQ Subsystem

Run the subsystem entry point from the repository root:

```bash
python3 aq/aq_main.py
```

`aq_main.py` is a scaffold for subsystem startup and coordination. It currently
prints the most recent sensor data when run and shows methods on how to upload
information to the server. The server function has not been implemented and a
proxy is put in place.

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

Add subsystem startup logic to `main()` in `aq_main.py` as it is developed.
