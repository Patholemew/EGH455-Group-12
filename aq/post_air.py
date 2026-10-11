from datetime import datetime, timezone

import requests
WVI_URL_AIR = "http://127.0.0.1:8000/api/air"

def send_to_wvi (sensor_readings):
    newest_readings = sensor_readings.recent_readings()
    cpu_temp = newest_readings[0]
    env_temp = newest_readings[1]
    oxidising = newest_readings[2]
    reducing = newest_readings[3]
    nh3 = newest_readings[4]
    light = newest_readings[5]
    humidity = newest_readings[6]
    pressure = newest_readings[7]
    timestamp = newest_readings[8]
    
    payload = {
        "captured_at": datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
        "temperature_c": env_temp,
        "pressure_hpa": pressure,
        "humidity_pct": humidity,
        "light_lux": light,
        "gas":
            {
                "reducing": reducing,
                "oxidising": oxidising,
                "ammonia": nh3
            },
    }
    with requests.post(WVI_URL_AIR, json=payload, timeout=1) as response:
        response.raise_for_status()
        return response.status_code