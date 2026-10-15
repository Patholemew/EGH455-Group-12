"""Entry point for the DE subsystem."""
from time import sleep
from gpiozero import Servo

GPIO_PIN = 13

DRILL_SPEED = 1
RETURN_SPEED = -1

DRILL_TIME_S = 10
PAUSE_TIME_S = 0.5
RETURN_TIME_S = 10

def main():
    """Run the DE subsystem."""
    servo = Servo(GPIO_PIN)

    try:
        servo.value = DRILL_SPEED
        sleep(DRILL_TIME_S)

        sleep(PAUSE_TIME_S)

        servo.value = RETURN_SPEED
        sleep(RETURN_TIME_S)

        
        sleep(0.2)
        servo.detach()
        servo.close()


if __name__ == "__main__":
    main()
