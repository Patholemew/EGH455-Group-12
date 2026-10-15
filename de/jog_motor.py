import argparse
from time import sleep
from gpiozero import Servo

GPIO_PIN = 13

def jog(direction: str, duration: float):
    """Run the servo in a given direction for a specified duration."""
    servo = Servo(GPIO_PIN)
    
    # Map direction choices to servo speeds (1.0 = forward/down, -1.0 = backward/up)
    speed = 1.0 if direction.lower() in ['forward', 'down', 'in'] else -1.0
    
    print(f"Running servo [{direction.lower()}] (speed: {speed}) for {duration} seconds...")
    
    try:
        servo.value = speed
        sleep(duration)
    finally:
        print("Stopping and detaching servo safely.")
        servo.value = 0
        sleep(0.1)  # Brief pause to ensure stop signal is sent
        servo.detach()
        servo.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jog the kinetic sand drill servo for calibration.")
    parser.add_argument(
        "direction", 
        choices=["forward", "backward", "down", "up", "in", "out"], 
        help="Direction to run the servo."
    )
    parser.add_argument(
        "duration", 
        type=float, 
        help="Duration in seconds to run the jog test."
    )
    
    args = parser.parse_args()
    jog(args.direction, args.duration)