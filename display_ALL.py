import sys
import numpy as np
import cv2
from PIL import Image
import st7735 as ST7735
import depthai as dai
from PIL import Image, ImageDraw, ImageFont
from fonts.ttf import RobotoMedium as UserFont
import logging
import subprocess

import time

from bme280 import BME280
from smbus2 import SMBus
'''Be sure to stop any other program running on the LCD panel before use
"sudo systemctl stop display_ip.service" to stop
"systemctl status display_ip.service" to check
'''



bus = SMBus(1)				#for temperature readings
bme280 = BME280(i2c_dev=bus)

# Get the temperature of the CPU for compensation
def get_cpu_temperature():
	with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
		temp = f.read()
		temp = int(temp) / 1000.0
	return temp


# Tuning factor for compensation. Decrease this number to adjust the
# temperature down, and increase to adjust up
factor = 2.25

cpu_temps = [get_cpu_temperature()] * 5

# Create ST7735 LCD display class.
# Create LCD class instance.
disp = ST7735.ST7735(
	port=0,
	cs=1,
	dc=9,
	backlight=12,
	rotation=270,
	spi_speed_hz=10000000
)
# Initialise display
disp.begin()
WIDTH = disp.width
HEIGHT = disp.height

pipeline = dai.Pipeline()
# Define source and output
camRgb = pipeline.create(dai.node.Camera)
camRgb.build()

# Properties
cameraOutput = camRgb.requestOutput(
	size=(300, 300),
	type = dai.ImgFrame.Type.RGB888p
	)
	
# Set font
font = ImageFont.load_default()

# Connect to device and start pipeline
previewQueue = cameraOutput.createOutputQueue(maxSize=4, blocking=False)
pipeline.start()
while pipeline.isRunning():
	#~~~CAMERA RELATED~~~#
	inFrame = previewQueue.get()
	frame = inFrame.getCvFrame()
	inRgb = previewQueue.get()
	img=inRgb.getCvFrame()
	img=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
	im_pil = Image.fromarray(img)
	# Resize the image
	im_pil = im_pil.resize((WIDTH, HEIGHT))
	
	#~~~~IP ADDRESS~~~~#	
	# Check IP address
	try:
		ip_output = subprocess.check_output(["hostname", "-I"], stderr=subprocess.STDOUT)
		ip = ip_output.decode("utf-8",errors="ignore").strip().split()[0]
	except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
		ip = "No IP"
	# Draw/"Type" IP address
	draw = ImageDraw.Draw(im_pil)
	draw.text((2, 2),f"IP Address: {ip}",fill=(255, 255, 255),font=font)
	#draw.text((50, 5),ip,fill=(0, 255, 0),font=font)
	
	#~~~~CHECK TEMP~~~~#
	cpu_temp = get_cpu_temperature()
	# Smooth out with some averaging to decrease jitter
	cpu_temps = cpu_temps[1:] + [cpu_temp]
	avg_cpu_temp = sum(cpu_temps) / float(len(cpu_temps))
	raw_temp = bme280.get_temperature()
	comp_temp = raw_temp - ((avg_cpu_temp - raw_temp) / factor)
	#logging.info(f"Compensated temperature: {comp_temp:05.2f} °C")
	#time.sleep(1.0)
	
	# Draw/"Type" Temperature
	draw.text((2, 60),f"Temp: {comp_temp:05.2f} °C",fill=(255, 255, 255),font=font)
	draw.text((2, 69),f"CPU Temp: {avg_cpu_temp:05.2f} °C",fill=(0, 255, 0),font=font)
	
	# Display image on lcd
	disp.display(im_pil)
	
	
	
