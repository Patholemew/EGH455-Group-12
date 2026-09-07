from gpiozero import Servo
from time import sleep

servo = Servo(12)

try:
    for x in range(6):
        servo.min()
        sleep(1.0)
        servo.mid()
        sleep(2.0)
        servo.max()
        sleep(1.0)
        print("testing servo loop" + str(x))

finally:
        servo.close()
print ("finished testing servo")