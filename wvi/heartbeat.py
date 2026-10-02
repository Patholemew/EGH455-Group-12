"""Periodic API check. Runs as its own process beside the web server."""
import time
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000"
INTERVAL = 10


def check():
    request = Request(BASE + "/api/heartbeat", data=b"", method="POST")
    with urlopen(request, timeout=3) as response:
        return response.status


def main():
    while True:
        try:
            check()
        except Exception as error:
            print("Heartbeat failed:", error, flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Heartbeat stopped.")