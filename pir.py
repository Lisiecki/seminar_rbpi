# !/usr/bin/python
# coding=utf-8

import time, sys
import RPi.GPIO as GPIO


GPIO.setmode(GPIO.BOARD)
GPIO.setup(7, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def motion(pin):
	print ("Bewegung erkannt")
	return
	
GPIO.add_event_detect(7, GPIO.RISING)
GPIO.add_event_callback(7, motion)

try:
	while True:
		time.sleep(0.5)
except KeyboardInterrupt:
	GPIO.cleanup()
	sys.exit()
			
