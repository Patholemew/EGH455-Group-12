import time
from bme280 import BME280

# Weather and Light
try:
    # Transitional fix for breaking change in LTR559
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559

# Gas readings
from enviroplus import gas

# BME280 temperature/pressure/humidity sensor
bme280 = BME280()
# Tuning factor for compensation. Decrease this number to adjust the
# temperature down, and increase to adjust up
factor = 2.25
CPU_AVERAGE_SAMPLES = 5


# Get average CPU Temperature
    # Run function with cpu_temps_record array to keep cpu temps averaging. Initialise empty cpu_temps_record array before running in loop.
def get_temperature(cpu_temps_record):
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            cpu_temp = f.read()
            cpu_temp = int(cpu_temp) / 1000.0
    cpu_temps_record = cpu_temps_record[-(CPU_AVERAGE_SAMPLES - 1):] + [cpu_temp]
    avg_cpu_temp = sum(cpu_temps_record) / float(len(cpu_temps_record))
    raw_temp = bme280.get_temperature()
    env_temp = raw_temp - ((avg_cpu_temp - raw_temp) / factor)
    return env_temp, cpu_temp

# Get all other sensor readings
def get_readings():
    proximity = ltr559.get_proximity()

    # variable = "humidity" | unit = "%"
    humidity = bme280.get_humidity()

    # variable = "light" | unit = "Lux"
    if proximity < 10:
        light = ltr559.get_lux()
    else:
        light = 1
    
    # variable = "pressure" | unit = "hPa"
    pressure = bme280.get_pressure()
        
    # variables = "gases" | unit = "kO"
    gases = gas.read_all()
    gases.oxidising = gases.oxidising / 1000   # variable = "oxidised"
    gases.reducing = gases.reducing / 1000     # variable = "reduced"
    gases.nh3 = gases.nh3 / 1000               # variable = "nh3"
    return humidity, light, gases, pressure


# Gases subcategories for "readings class"
class gases:
    def __init__(self):
        self.oxidising = []
        self.reducing = []
        self.nh3 = []

# Class to run all sensor data immediately
class readings:
    """Keeps Record of All Sensor Readings"""
    # Send the entire class to the server to get all information in a nice neat package
    gas_unit = "kO"
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
    
    def record_data(self):
        """Runs functions to record the sensor data immediately"""
        env_temp, cpu_temp = get_temperature(self.cpu_temps_record)
        humidity, light, gases, pressure = get_readings()
        
        self.cpu_temps_record.append(cpu_temp)
        self.env_temps_record.append(env_temp)
        self.gases.oxidising.append(gases.oxidising)
        self.gases.reducing.append(gases.reducing)
        self.gases.nh3.append(gases.nh3)
        self.light.append(light)
        self.humidity.append(humidity)
        self.pressure.append(pressure)
        self.timestamp.append(time.time())


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
        Light:       {light} {self.light_unit}\n
        Oxidised:    {oxidising} {self.gas_unit}\n
        Reduced:     {reducing} {self.gas_unit}\n
        nh3:         {nh3} {self.gas_unit}\n''')
        



