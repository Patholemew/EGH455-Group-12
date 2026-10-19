"""Select the LCD screen using the proximity sensor or WVI dashboard."""

import json
import subprocess
import time
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont


DETECTED = 1  # Finger detection threshold; adjust for the sensor if needed.
LCD_ROTATION = 90 # Change to 90 if using alternative payload case which flips the LCD panel

FRAME_PATH = "/dev/shm/uav/liveimage.jpg"
DATA_URL = "http://127.0.0.1:8000/api/data"
LCD_URL = "http://127.0.0.1:8000/api/lcd"

# These values match the dashboard's /api/lcd control.
IP_ADDRESS = 1
TEMPERATURE = 2
VIDEO_FEED = 3
DEFAULT = 4


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


def update_website_pane(pane):
    """Save a sensor selection so the website and LCD stay in sync."""
    request = Request(
        LCD_URL,
        data=json.dumps({"pane": pane}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=0.5):
            pass
    except OSError:
        # Local switching still works offline; polling resyncs when WVI returns.
        print("Could not save LCD selection to WVI", flush=True)


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

    # Support the same LTR559 library versions as AQFunctions.py.
    ltr559 = None

    try:
        from ltr559 import LTR559
        try:
            ltr559 = LTR559()
        except Exception as e:
            print(f"Warning: LTR559 failed to initialise: {e}")
    except ImportError:
        try:
            import ltr559
        except ImportError as e:
            print(f"Warning: LTR559 library unavailable: {e}")

    display = st7735.ST7735(
        port=0,
        cs=1,
        dc=9,
        backlight=12,
        rotation=LCD_ROTATION,
        spi_speed_hz=10000000,
    )
    display.begin()

    size = (display.width, display.height)
    font = ImageFont.load_default()
    cpu_temps = [get_cpu_temperature()] * 5
    LCD_PANE = IP_ADDRESS
    temperature = "Unavailable"
    ip = "No IP"
    next_update = 0.0

    pressing_sensor = False
    press_count = 0
    release_count = 0
    REQUIRED_READINGS = 2

    while True:
        # Poll the website's selection, temperature and IP once per second.
        if time.monotonic() >= next_update:
            LCD_PANE, temperature = get_display_data(LCD_PANE)
            ip = get_ip()
            next_update = time.monotonic() + 1

        cpu_temps = cpu_temps[1:] + [get_cpu_temperature()]
        valid_temps = [value for value in cpu_temps if value is not None]
        cpu_temp = sum(valid_temps) / len(valid_temps) if valid_temps else None

        # Advance once per stable press, then wait for a stable release.
        try:
            prox = ltr559.get_proximity()
        except OSError:
            prox = None
        if prox is None:
            # Preserve the press state, but restart the valid-reading sequence.
            press_count = 0
            release_count = 0
        elif prox >= DETECTED:
            release_count = 0
            press_count += 1
            if not pressing_sensor and press_count >= REQUIRED_READINGS:
                pressing_sensor = True
                LCD_PANE += 1
                if LCD_PANE == DEFAULT:
                    LCD_PANE = IP_ADDRESS
                update_website_pane(LCD_PANE)
        else:
            press_count = 0
            release_count += 1
            if release_count >= REQUIRED_READINGS:
                pressing_sensor = False

        image = render_screen(LCD_PANE, size, font, ip, temperature, cpu_temp)
        display.display(image)
        time.sleep(0.2)


if __name__ == "__main__":
    main()
