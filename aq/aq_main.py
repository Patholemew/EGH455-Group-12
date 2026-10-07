"""Entry point for the AQ subsystem."""
import AQFunctions      #import functions from AQFunctions.py file
import argparse         #import argparse which allows me to easily run tests by passing an argument into the terminal
from post_air import send_to_wvi
import requests
import time

sensor_readings = AQFunctions.readings()    #Initialise "readings" class

#SEND2SERVER = 0     # Variable in place of WVI function - code is a proxy

# agruments setup
parser = argparse.ArgumentParser()
parser.add_argument("-t","--Test", help="Runs REQ-F-03 testing conditions, enables terminal printing.")
parser.add_argument("-h","--HistTest", help="Runs REQ-F-06 testing conditions, checks historical data can be retrieved. (Enables terminal printing)")
parser.add_argument("-n","--NoWVI", help="Runs program without involving the WVI subsystem")
parser.add_argument("-w","--Once", help="Runs program once, single loop, no repeating.")
parser.add_argument("-l","--lightweight", help="Runs WVI in lightweight mode")
args = parser.parse_args()

RECALL_AFTER = 10 #For historical test, program will attempt to recall the first reading after RECALL_AFTER runs.

def main():
    """Run the AQ subsystem."""
    # Should be running continuously to save data, or use lightweight method
    PRINT2TERMINAL = False
    if args.Test:
        print("Running REQ-F-03 Test as described in doc. P-AQ12-TR_26v1, section 5\n")
        PRINT2TERMINAL = True
    elif args.HistTest:
        print("Running REQ-F-06 Test as described in doc. P-AQ12-TR_26v1, section 5\n")
        PRINT2TERMINAL = True
    if args.NoWVI:
        print("Disabling Web Server functionality...\n")
    elif args.lightweight:
        print("Changing Web Server request to lightweight model...\n")
    
    if args.Once:
        print("Running aq_main.py once...\n")
        REPEAT = False
        try:
            sensor_readings.record_data()
            if args.Test or agrs.HistTest:
                sensor_readings.print_data()    #For Testing, prints to terminal
            if args.HistTest and len(sensor_readings.timestamp())==5:
                print(f'''__Historical Test - First Reading Recollection__        
                TIME:        {sensor_readings.timestamp[0]}\n
                Temperature: {sensor_readings.env_temps_record[0]} {sensor_readings.temp_unit}\n
                Pressure:    {sensor_readings.pressure[0]} {sensor_readings.pressure_unit}\n
                Humidity:    {sensor_readings.humidity[0]} {sensor_readings.humidity_unit}\n
                Light:       {sensor_readings.light[0]} {sensor_readings.light_unit}\n
                Oxidised:    {sensor_readings.gases.oxidising[0]} {sensor_readings.gas_unit}\n
                Reduced:     {sensor_readings.gases.reducing[0]} {sensor_readings.gas_unit}\n
                nh3:         {sensor_readings.gases.nh3[0]} {sensor_readings.gas_unit}\n
                __READING RETRIEVAL SUCCESS__\n''')
            if !(args.NoWVI):
                try:
                    if args.lightweight:
                        # Lightweight way to get information for sending to server
                        send_to_wvi(list(sensor_readings.recent_readings()))
                    else:
                        send_to_wvi(sensor_readings)
                except request.RequestException as e:
                    print(f"WVI API POST FAILURE: {e}")
        except Exception as e:
            print(f"AQ READING FAILURE: {e}")
    else:
        REPEAT = True
    
    while REPEAT:
        timestamp = time.monotonic()
        try:
            sensor_readings.record_data()
            if args.Test or agrs.HistTest:
                sensor_readings.print_data()    #For Testing, prints to terminal
            if args.HistTest and len(sensor_readings.timestamp())==RECALL_AFTER:
                print(f'''__Historical Test - First Reading Recollection__        
                TIME:        {sensor_readings.timestamp[0]}\n
                Temperature: {sensor_readings.env_temps_record[0]} {sensor_readings.temp_unit}\n
                Pressure:    {sensor_readings.pressure[0]} {sensor_readings.pressure_unit}\n
                Humidity:    {sensor_readings.humidity[0]} {sensor_readings.humidity_unit}\n
                Light:       {sensor_readings.light[0]} {sensor_readings.light_unit}\n
                Oxidised:    {sensor_readings.gases.oxidising[0]} {sensor_readings.gas_unit}\n
                Reduced:     {sensor_readings.gases.reducing[0]} {sensor_readings.gas_unit}\n
                nh3:         {sensor_readings.gases.nh3[0]} {sensor_readings.gas_unit}\n
                __READING RETRIEVAL SUCCESS__\n''')
            if not args.NoWVI:
                try:
                    if args.lightweight:
                        # Lightweight way to get information for sending to server
                        send_to_wvi(list(sensor_readings.recent_readings()))
                    else:
                        send_to_wvi(sensor_readings)
                except request.RequestException as e:
                    print(f"WVI API POST FAILURE: {e}")
        except Exception as e:
            print(f"AQ READING FAILURE: {e}")
        time.sleep(max(0,1-(time.monotonic()-timestamp)))
        
        
    '''
    sensor_readings.record_data()
    
    sensor_readings.print_data()    # For Testing, prints to terminal

    # Lightweight way to get information for sending to server
    cpu_temp, env_temp, oxidising, reducing, nh3, light, humidity, pressure, timestamp = sensor_readings.recent_readings()
    SEND2SERVER = [cpu_temp, env_temp, oxidising, reducing, nh3, light, humidity, pressure, timestamp] # Sends just recent sensor reading
    # Simpler way to write the lightweight method.
    SEND2SERVER = list(sensor_readings.recent_readings())

    # Sends entire sensor readings class
    SEND2SERVER = sensor_readings  

    print("AQ subsystem main is not fully tested yet.")'''


if __name__ == "__main__":
    try:
        main()
    except Keyboard Interrupt:
        print("AQ stopped")
