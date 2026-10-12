import fcntl
import math
import os
from pathlib import Path
import sys
import time
import requests
import AQFunctions

from post_air import send_to_wvi


def collect_and_publish(sensor_readings, warmup_seconds):
    # Start timing after the first successful read: the gas driver enables its
    # heater lazily, so sleeping before reading does not warm the sensor up.
    ready_at = None
    print(f"AQ settling for {warmup_seconds:g}s before publishing", flush=True)
    while True:
        started = time.monotonic()
        try:
            sensor_readings.record_data()
            if ready_at is None:
                ready_at = time.monotonic() + warmup_seconds
            elif time.monotonic() >= ready_at:
                send_to_wvi(sensor_readings)
        except requests.RequestException as error:
            print(f"WVI POST failed: {error}", flush=True)
        except OSError as error:
            print(f"Sensor reading failed: {error}", flush=True)

        time.sleep(max(0, 1 - (time.monotonic() - started)))

def main():
    warmup_seconds = float(os.environ.get("AQ_WARMUP_SECONDS", "30"))
    if not math.isfinite(warmup_seconds) or warmup_seconds < 0:
        raise ValueError("AQ_WARMUP_SECONDS must be finite and non-negative")
    lock_path = Path.home() / ".cache" / "uav" / "aq.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("AQ is already running. Stop aq.service first.")
            return 1
        sensor_readings = AQFunctions.readings()

        collect_and_publish(sensor_readings, warmup_seconds)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("AQ stopped")
