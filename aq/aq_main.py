import fcntl
from pathlib import Path
import sys
import time
import requests
import AQFunctions

from post_air import send_to_wvi

def main():
    lock_path = Path.home() / ".cache" / "uav" / "aq.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("AQ is already running. Stop aq.service first.")
            return 1
        sensor_readings = AQFunctions.readings()

        while True:
            started = time.monotonic()

            try:
                sensor_readings.record_data()
                send_to_wvi(sensor_readings)
            except requests.RequestException as error:
                print(f"WVI POST failed: {error}", flush=True)
            except OSError as error:
                print(f"Sensor reading failed: {error}", flush=True)

            time.sleep(max(0, 1 - (time.monotonic() - started)))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("AQ stopped")
