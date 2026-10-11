"""Display the LCD screen selected from the WVI dashboard."""

import json
import subprocess
import time
from collections import deque
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont


FRAME_PATH = "/dev/shm/uav/liveimage.jpg"
DATA_URL = "http://127.0.0.1:8000/api/data"

# These values match the dashboard's /api/lcd control.
IP_ADDRESS = 1
TEMPERATURE = 2
VIDEO_FEED = 3


def get_display_data(current_pane):
    """Read the requested screen and air temperature in one WVI request.

    Keep the last selected screen if WVI is temporarily unavailable.
    """
    try:
        with urlopen(DATA_URL, timeout=0.5) as response:
            data = json.load(response)
        if not isinstance(data, dict):
            return current_pane, "Unavailable"
    except (OSError, ValueError):
        return current_pane, "Unavailable"

    lcd = data.get("lcd")
    if isinstance(lcd, dict):
        pane = lcd.get("pane")
        if type(pane) is int and pane in (IP_ADDRESS, TEMPERATURE, VIDEO_FEED):
            current_pane = pane

    try:
        air = data["air"]
        if air is None:
            temperature = "Unavailable"
        elif air["stale"]:
            temperature = "Stale"
        else:
            temperature = f'{float(air["temperature_c"]):.2f} °C'
    except (ValueError, KeyError, TypeError):
        temperature = "Unavailable"
    return current_pane, temperature


def get_cpu_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as file:
            return int(file.read()) / 1000.0
    except (OSError, ValueError):
        return None


def get_ip():
    try:
        output = subprocess.check_output(["hostname", "-I"], timeout=1)
        return output.decode().split()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return "No IP"


def render_screen(pane, size, font, ip, temperature, cpu_temp):
    if pane == VIDEO_FEED:
        try:
            with Image.open(FRAME_PATH) as frame:
                return frame.convert("RGB").resize(size)
        except (OSError, ValueError):
            pass  # Draw the missing-frame message below.

    image = Image.new("RGB", size, "black")
    draw = ImageDraw.Draw(image)
    if pane == VIDEO_FEED:
        draw.text((2, 2), "No video frame", fill="white", font=font)
    elif pane == TEMPERATURE:
        draw.text((2, 8), "Temp: " + temperature, fill="white", font=font)
        cpu_text = "Unavailable" if cpu_temp is None else f"{cpu_temp:.2f} °C"
        draw.text((2, 30), "CPU Temp: " + cpu_text, fill="lime", font=font)
    else:
        draw.text((2, 2), "IP Address:", fill="white", font=font)
        draw.text((2, 20), ip, fill="white", font=font)
    return image


def main():
    # Only the LCD process needs the Raspberry Pi display driver.
    import st7735

    display = st7735.ST7735(
        port=0,
        cs=1,
        dc=9,
        backlight=12,
        rotation=270,
        spi_speed_hz=10000000,
    )
    display.begin()

    size = (display.width, display.height)
    font = ImageFont.load_default()
    cpu_temps = deque(maxlen=5)  # Automatically keep only the five latest readings.
    pane = IP_ADDRESS
    temperature = "Unavailable"
    ip = "No IP"
    next_update = 0.0

    while True:
        # Poll the website's selection, temperature and IP once per second.
        if time.monotonic() >= next_update:
            pane, temperature = get_display_data(pane)
            ip = get_ip()
            next_update = time.monotonic() + 1

        cpu_temps.append(get_cpu_temperature())
        valid_temps = [value for value in cpu_temps if value is not None]
        cpu_temp = sum(valid_temps) / len(valid_temps) if valid_temps else None
        image = render_screen(pane, size, font, ip, temperature, cpu_temp)
        display.display(image)
        time.sleep(0.2)


if __name__ == "__main__":
    main()
