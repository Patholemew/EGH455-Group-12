"""Entry point for the AQ subsystem."""
import AQFunctions      #import functions from AQFunctions.py file
from post_air import send_to_wvi
import requests
import time

sensor_readings = AQFunctions.readings()    #Initialise "readings" class

SEND2SERVER = 0     # Variable in place of WVI function - code is a proxy

def main():
    """Run the AQ subsystem."""
    while True:
        timestamp = time.monotonic()
        try:
            sensor_readings.record_data()
            send_to_wvi(sensor_readings)
            # sensor_readings.print_data()    # For Testing, prints to terminal
        except requests.RequestException as e:
            print(f"WVI API POST FAILURE: {e}")
        except Exception as e:
            print(f"AQ reading failed")
        time.sleep(max(0, 1 - (time.monotonic() - timestamp)))

    # Should be running continuously to save data, or use lightweight method

    # Lightweight way to get information for sending to server
    # cpu_temp, env_temp, oxidising, reducing, nh3, light, humidity, pressure, timestamp = sensor_readings.recent_readings()
    # SEND2SERVER = [cpu_temp, env_temp, oxidising, reducing, nh3, light, humidity, pressure, timestamp] # Sends just recent sensor reading
    # Simpler way to write the lightweight method.
    # SEND2SERVER = list(sensor_readings.recent_readings())

    # Sends entire sensor readings class
    # SEND2SERVER = sensor_readings  

    # print("AQ subsystem main is not fully tested yet.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("AQ stopped")
