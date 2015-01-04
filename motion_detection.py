from __future__ import division
#!/usr/bin/python3

import picamera
import numpy as np
import RPi.GPIO as gpio
import time

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
        self.first_third = round(self.cols / 3)
        self.second_third = round((self.cols / 3) * 2)
        self.last_third = self.cols

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
            gpio.output(motion_detected_led, gpio.HIGH)
           #print('data {0}'.format(data.shape))
            for i in data:
                f = data[0, self.first_third - 1]
                s = data[self.first_third, self.second_third - 1]
                l = data[self.second_third, self.last_third - 1]
                #if (f > l):
                #    print("links")
                #elif (s > l) and (s > f):
                #    print("mitte")
                #elif (l > f):
                #    print("rechts")
                #elif (s < f) and (s < l):
                #    print("mitte")
                #else:
                #    print("nothing!")
        else:
            gpio.output(motion_detected_led, gpio.LOW)
        # Pretend we wrote all the bytes of s
        return len(s)

with picamera.PiCamera() as camera:
    gpio.setmode(gpio.BOARD)
    gpio.setup(motion_detected_led, gpio.OUT)
    #Turn the camera's LED off
    #camera.led = False
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
