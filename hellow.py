import time, sys
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BOARD)
GPIO.setup(5, GPIO.OUT)
time.sleep(5)
GPIO.output(5, GPIO.LOW)
GPIO.cleanup()

print("Hello World!")
