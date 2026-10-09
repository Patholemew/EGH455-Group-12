import json
import subprocess
import time
from urllib.error import URLError
from urllib.request import urlopen

import st7735
from PIL import Image, ImageDraw, ImageFont

DETECTED = 1  #detecting finger press on sensor

FRAME_PATH = "/dev/shm/uav/liveimage.jpg"
DATA_URL = "http://127.0.0.1:8000/api/data"

IP_ADDRESS = 1
TEMPERATURE = 2
VIDEO_FEED = 3
DEFAULT = 4
LCD_PANE = IP_ADDRESS

def get_temperature():
    try:
        with urlopen(DATA_URL, timeout=0.5) as response:
            air = json.load(response)["air"]

        if air is None:
            return "Unavailable"

        if air["stale"]:
            return "Stale"

        return f'{float(air["temperature_c"]):.2f} °C'

    except (URLError, OSError, ValueError, KeyError, TypeError):
        return "Unavailable"


def get_cpu_temperature():
    with open("/sys/class/thermal/thermal_zone0/temp") as file:
        return int(file.read()) / 1000.0


def get_ip():
    try:
        output = subprocess.check_output(["hostname", "-I"], timeout=1)
        return output.decode().split()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return "No IP"


display = st7735.ST7735(
    port=0,
    cs=1,
    dc=9,
    backlight=12,
    rotation=270,
    spi_speed_hz=10000000
)
display.begin()

size = (display.width, display.height)
font = ImageFont.load_default()
cpu_temps = [get_cpu_temperature()] * 5

temperature = "Unavailable"
ip = "No IP"
next_update = 0.0

while True:
    # Update temperature and IP once per second.
    if time.monotonic() >= next_update:
        temperature = get_temperature()
        ip = get_ip()
        next_update = time.monotonic() + 1
    
    cpu_temps = cpu_temps[1:] + [get_cpu_temperature()]
    cpu_temp = sum(cpu_temps) / len(cpu_temps)
    # Get proximity value (checks if button pressed to switch screens)
    prox = ltr559.get_proximity()
    if prox => DETECTED:
      LCD_PANE += 1 # or LCD_PANE = LCD_PANE + 1 (switches screen)
    '''LCD_PANE = WVI_BUTTON #assign value to switch case to change it'''
    switch (LCD_PANE) {
      case IP_ADDRESS:
        image = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.text((2, 2), "IP Address: " + ip, fill="white", font=font)
    
      case TEMPERATURE
        image = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.text(
            (2, 60),
            "Temp: " + temperature, 
            fill="white", font=font
        )
        draw.text(
            (2, 69),
            f"CPU Temp: {cpu_temp:.2f} °C",
            fill="lime",
            font=font
        )
    
      case VIDEO_FEED:
        try:
            with Image.open(FRAME_PATH) as frame:
                image = frame.convert("RGB").resize(size)
        except (OSError, ValueError):
            image = Image.new("RGB", size, (0, 0, 0))
      case DEFAULT:
        LCD_PANE = IP_ADDRESS
    }

    display.display(image)
    time.sleep(0.2)
