import time
from bme280 import BME280
from smbus2 import SMBus
import numpy as np
# Create a single shared SMBus instance (just like display_ALL.py)
bus = SMBus(1)

# Weather and Light
# Safely import the module without forcing immediate hardware connection
try:
    from ltr559 import LTR559
    LTR559_AVAILABLE = True
except ImportError:
    LTR559_AVAILABLE = False

# Keep a global or lazy-loaded instance variable
_ltr559_instance = None

def get_ltr559():
    global _ltr559_instance
    if _ltr559_instance is None and LTR559_AVAILABLE:
        try:
            _ltr559_instance = LTR559(i2c_dev=bus)
        except Exception as e:
            print(f"Warning: Could not initialize LTR559 sensor: {e}")
    return _ltr559_instance
    
# Gas readings
from enviroplus import gas

# BME280 temperature/pressure/humidity sensor using the shared bus
bme280 = BME280(i2c_dev=bus)

# Tuning factor for compensation. Decrease this number to adjust the
# temperature down, and increase to adjust up
factor = 2.25

CALIBRATION_TIME = 10 #ten minutes required until calribation of gases
# Get average CPU Temperature
    # Run function with cpu_temps_record array to keep cpu temps averaging. Initialise empty cpu_temps_record array before running in loop.
def get_temperature(cpu_temps_record):
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            cpu_temp = f.read()
            cpu_temp = int(cpu_temp) / 1000.0
    cpu_temps_record = cpu_temps_record[1:] + [cpu_temp]
    avg_cpu_temp = sum(cpu_temps_record) / float(len(cpu_temps_record))
    raw_temp = bme280.get_temperature()
    env_temp = raw_temp - ((avg_cpu_temp - raw_temp) / factor)
    return env_temp, cpu_temp

# Gases subcategories for "readings class"
class gases:
    def __init__(self):
        self.oxidising = []
        self.reducing = []
        self.nh3 = []

# Get all other sensor readings
def get_readings():
    ltr559 = get_ltr559()
    
    if ltr559  is not None:
        try:
            proximity = ltr559.get_proximity()
            # variable = "light" | unit = "Lux"
            if proximity < 10:
                light = ltr559.get_lux()
            else:
                light = 1
        except Exception:
            light = 0  # Fallback value if I2C glitches mid-run
    else:
        light = 0

    # variable = "humidity" | unit = "%"
    humidity = bme280.get_humidity()
    
    # variable = "pressure" | unit = "hPa"
    pressure = bme280.get_pressure()
    
    # variables = "gases" | unit = "kO"
    gases = gas.read_all()
    gases.oxidising = gases.oxidising / 1000   # variable = "oxidised"
    gases.reducing = gases.reducing / 1000     # variable = "reduced"
    gases.nh3 = gases.nh3 / 1000               # variable = "nh3"
    return humidity, light, gases, pressure

class GasBaseline:
    def __init__(self):
        self.oxidising = 0.0
        self.reducing = 0.0
        self.nh3 = 0.0

def simulate_readings(cpu_temps_record):
    '''Generates realistic fallback data if replacement enviro+ is not available and features still need to show 
    that they function if not for the sensors'''
    #CPU Temp simulation
    last_cpu = cpu_temps_record[-1] if cpu_temps_record else 45.0 #if list empty use 45 otherwise fluctuate temp
    cpu_temp = max(35.0, min(65.0, last_cpu + random.uniform(-0.5, 0.5)))
    # Environment Temp between 19C and 25C
    env_temp = 21.0+2.0 * np.sin(time.time() / 3600) + random.uniform(-0.1, 0.1)
    # simulate other metric
    humidity = max(10.0, min(95.0, 50.0 + 10.0* np.sin(time.time() / 7200) + random.uniform(-0.5, 0.5)))
    pressure = max(950.0, min(1050.0, 1013.25 + random.uniform(-0.2, 0.2)))
    # Simulate lux level by time of day and occasional proximity mock
    light = max(0.0, 300.0 + 250.0 * np.sin(time.time() / 43200) + random.uniform(-5, 5))
    # Gas sim
    class MockGasReadings:
        def __init__(self):
            # Base values in kOhms
            self.oxidising = (3000 + random.uniform(-200, 200)) / 1000.0
            self.reducing = (250000 + random.uniform(-1500, 1500)) / 1000.0
            self.nh3 = (120000 + random.uniform(-800, 800)) / 1000.0
    gases_mock = MockGasReadings()

    return env_temp, cpu_temp, humidity, light, gases_mock, pressure


# Class to run all sensor data immediately
class readings:
    """Keeps Record of All Sensor Readings"""
    # Send the entire class to the server to get all information in a nice neat package
    gas_unit = "ppm"
    resistive_unit = "kOhm" #Old Gas unit before conversion
    light_unit = "Lux"
    humidity_unit = "%"
    temp_unit = "°C"
    pressure_unit = "hPa"
    start_time = time.time()
    def __init__(self):
        self.cpu_temps_record = []
        self.env_temps_record = []
        self.gases = gases()
        self.light = []
        self.humidity = []
        self.pressure = []
        self.timestamp = []
        self.CALIBRATED = False
        self.PREV_PPM = False    #checks if the previous recorded data has been converted to ppm based on the baseline
        self.gas_baseline = GasBaseline()
    def convert2ppm_prev(self):    #ensures WVI can convert previous data in storage to ppm values assuming stored in readings class
        print("Calibrating Historical Gas Values...\n")
        oxy_const = 1/0.9804
        red_const = -1/0.8526
        nh3_const = -1/1.9641
        i = 0
        while ((self.timestamp[i] - self.start_time) <= CALIBRATION_TIME*60):
            oxy_ratio = abs(self.gases.oxidising[i] / self.gas_baseline.oxidising) #Rs/R0 - abs() to ensure log doesn't fail
            red_ratio = abs(self.gases.reducing[i] / self.gas_baseline.reducing) #Rs/R0
            nh3_ratio = abs(self.gases.nh3[i] / self.gas_baseline.nh3) #Rs/R0
            self.gases.oxidising[i] = 10**(oxy_const*(np.log10(oxy_ratio) - 0.7813))
            self.gases.reducing[i] = 10**(red_const*(np.log10(red_ratio) - 0.5587))
            self.gases.nh3[i] = 10**(nh3_const*(np.log10(nh3_ratio) + 0.3347))
            i += 1
        print("Calibration of Previous Gas Values Complete!\n")
        self.PREV_PPM = True
        
    def convert2ppm(self):
        if self.CALIBRATED:
            #Oxidation
            oxy_ratio = abs(self.gases.oxidising[-1] / self.gas_baseline.oxidising) #Rs/R0 - abs() to ensure log doesn't fail
            oxy_const = 1/0.9804
            oxy_ppm = 10**(oxy_const*(np.log10(oxy_ratio) - 0.7813))
            #Reduction
            red_ratio = abs(self.gases.reducing[-1] / self.gas_baseline.reducing) #Rs/R0
            red_const = -1/0.8526
            red_ppm = 10**(red_const*(np.log10(red_ratio) - 0.5587))
            #Reduction
            nh3_ratio = abs(self.gases.nh3[-1] / self.gas_baseline.nh3) #Rs/R0
            nh3_const = -1/1.9641
            nh3_ppm = 10**(nh3_const*(np.log10(nh3_ratio) + 0.3347))
            # Replace resistance value with recalibrated values
            self.gases.oxidising[-1] = oxy_ppm
            self.gases.reducing[-1] = red_ppm
            self.gases.nh3[-1] = nh3_ppm
        # else keep uncalibrated values until chosen R0 value and run automatic historical calibration

        if  self.CALIBRATED and not self.PREV_PPM:
            #Historical calibration
            convert2ppm_prev(self) #updates previous values to be in ppm

    def record_data(self, SIMULATE = FALSE):
        """Runs functions to record the sensor data immediately"""
        if SIMULATE:
            # Simulate if SIMULATE flag is true (implies hardware is broken still)
            env_temp, cpu_temp, humidity, light, gases_data, pressure = simulate_readings(self.cpu_temps_record)
        else:
            try:
                env_temp, cpu_temp = get_temperature(self.cpu_temps_record)
                humidity, light, gases, pressure = get_readings()
            except Exception as e:
                print(f"Hardware read failed ({e}).")
        
        if ((timestamp[-1] - self.start_time) > CALIBRATION_TIME*60) and self.CALIBRATED == False  #greater than ten minutes (in seconds) activate only once.
            #Expected time for gas sensing to stablise (calibration window)
            self.CALIBRATED = True
            self.gas_baseline.oxidising = gases.oxidising
            self.gas_baseline.reducing = gases.reducing
            self.gas_baseline.nh3 = gases.nh3
    
        self.cpu_temps_record.append(cpu_temp)
        self.env_temps_record.append(env_temp)
        self.gases.oxidising.append(gases.oxidising)
        self.gases.reducing.append(gases.reducing)
        self.gases.nh3.append(gases.nh3)
        convert2ppm(self)    #checks if calibrated and if so applies conversion to ppm.
        self.light.append(light)
        self.humidity.append(humidity)
        self.pressure.append(pressure)
        self.timestamp.append(time.time()-self.start_time)


    def recent_readings(self):
        """Lightweight way of Transferring Data to Server"""
        # Reads the most recent/last data in the array
        cpu_temp = self.cpu_temps_record[-1]
        env_temp = self.env_temps_record[-1]
        oxidising = self.gases.oxidising[-1]
        reducing = self.gases.reducing[-1]
        nh3 = self.gases.nh3[-1]
        light = self.light[-1]
        humidity = self.humidity[-1]
        pressure = self.pressure[-1]
        timestamp = self.timestamp[-1]
        return cpu_temp, env_temp, oxidising, reducing, nh3, light, humidity, pressure, timestamp

    def manual_record_data(self, cpu_temp, env_temp, oxidising, reducing, nh3, light, humidity, pressure, timestamp):
        """For the lightweight method: it may be useful to manually record the history yourself in new class
            rather than sending the entire class each time you want new data."""
        # Does not automatically sort by time - be cautious when using.
        self.cpu_temps_record.append(cpu_temp)
        self.env_temps_record.append(env_temp)
        self.gases.oxidising.append(oxidising)
        self.gases.reducing.append(reducing)
        self.gases.nh3.append(nh3)
        self.light.append(light)
        self.humidity.append(humidity)
        self.pressure.append(pressure)
        self.timestamp.append(timestamp)

    def print_data(self):
        """Prints most recent data to the Terminal"""
        cpu_temp, env_temp, oxidising, reducing, nh3, light, humidity, pressure, timestamp = self.recent_readings()
        print(f'''        TIME: {timestamp}\n
        Temperature: {env_temp} {self.temp_unit}\n
        Pressure:    {pressure} {self.pressure_unit}\n
        Humidity:    {humidity} {self.humidity_unit}\n
        Light:       {light} {self.light_unit}\n''')
        if timestamp > CALIBRATION_TIME*60:
            print(f'''Oxidised:    {oxidising} {self.gas_unit}\n
        Reduced:     {reducing} {self.gas_unit}\n
        nh3:         {nh3} {self.gas_unit}\n''')
        else:
        print(f'''Oxidised:    {oxidising} {self.resistive_unit}\n
        Reduced:     {reducing} {self.resistive_unit}\n
        nh3:         {nh3} {self.resistive_unit}\n''')
        



