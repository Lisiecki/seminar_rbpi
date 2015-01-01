from __future__ import division
#!/usr/bin/python3

import picamera
import numpy as np
import RPi.GPIO as gpio
import time
import subprocess

motion_dtype = np.dtype([
    ('x', 'i1'),
    ('y', 'i1'),
    ('sad', 'u2'),
    ])

motion_detected_led = 40

class MyMotionDetector(object):

    def __init__(self, camera):
        width, height = camera.resolution
        self.cols = (width + 15) // 16
        self.cols += 1 # there's always an extra column
        self.rows = (height + 15) // 16

    def write(self, s):
        # Load the motion data from the string to a numpy array
        data = np.fromstring(s, dtype=motion_dtype)
        # Re-shape it and calculate the magnitude of each vector
        data = data.reshape((self.rows, self.cols))
        data = np.sqrt(
            np.square(data['x'].astype(np.float)) +
            np.square(data['y'].astype(np.float))
            ).clip(0, 255).astype(np.uint8)
        # If there're more than 10 vectors with a magnitude greater
        # than 60, then say we've detected motion
        if (data > 60).sum() > 10:
			returncode = subprocess.call(['sudo python3 pir.py'])
            gpio.output(motion_detected_led, gpio.HIGH)
        else:
            gpio.output(motion_detected_led, gpio.LOW)
        # Pretend we wrote all the bytes of s
        return len(s)

with picamera.PiCamera() as camera:
    gpio.setmode(gpio.BOARD)
    gpio.setup(motion_detected_led, gpio.OUT)
    camera.resolution = (640, 480)
    camera.framerate = 30
    camera.start_recording(
        # Throw away the video data, but make sure we're using H.264
        '/dev/null', format='h264',
        # Record motion data to our custom output object
        motion_output=MyMotionDetector(camera)
        )
    camera.wait_recording(30)
    camera.stop_recording()
    gpio.output(motion_detected_led, gpio.LOW)
    gpio.cleanup()
