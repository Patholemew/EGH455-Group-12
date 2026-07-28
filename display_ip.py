import subprocess
import st7735
from PIL import Image, ImageDraw, ImageFont

try:
    ip_output = subprocess.check_output(["hostname", "-I"], stderr=subprocess.STDOUT)
    ip = ip_output.decode("utf-8", errors="ignore").strip().split()[0]
except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
    ip = "No IP"

img = Image.new("RGB", (160, 80), (0, 0, 0,))
draw = ImageDraw.Draw(img)
font = ImageFont.load_default()

# Create LCD class instance.
disp = st7735.ST7735(
    port=0,
    cs=1,
    dc="GPIO9",
    backlight="GPIO12",
    rotation=270,
    spi_speed_hz=10000000
)

# Initialize display.
disp.begin()

# Width and height to calculate text position.
WIDTH = disp.width
HEIGHT = disp.height

draw.text((5, 10), "IP Address",
          fill = (255, 255, 255), font=font)
draw.text((5, 35), ip, fill=(0, 255, 0), font=font)

disp.display(img)