from __future__ import division
#!/usr/bin/python3

import picamera
import numpy as np
import RPi.GPIO as GPIO
import time, sys

motion_dtype = np.dtype([
    ('x', 'i1'),
    ('y', 'i1'),
    ('sad', 'u2'),
    ])

motion_detected_led = 40
pir_motion_detected_led = 5
pir_out = 7
no_motion_cnt = 0
pir_event_enabled = 0

class MyMotionDetector(object):

    def __init__(self, camera):
        width, height = camera.resolution
        self.cols = (width + 15) // 16
        self.cols += 1 # there's always an extra column
        self.rows = (height + 15) // 16

    def motion(self, pin):
        GPIO.output(pir_motion_detected_led, GPIO.HIGH)
        return

    def write(self, s):
        global no_motion_cnt
        global pir_event_enabled

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
            GPIO.output(motion_detected_led, GPIO.HIGH)
            no_motion_cnt = 0
            if pir_event_enabled == 0:
                pir_event_enabled = 1
                GPIO.add_event_detect(pir_out, GPIO.RISING)
                GPIO.add_event_callback(pir_out, self.motion)
        else:
            if no_motion_cnt == 40:
                GPIO.output(motion_detected_led, GPIO.LOW)
                GPIO.output(pir_motion_detected_led, GPIO.LOW)
                GPIO.remove_event_detect(pir_out)
                pir_event_enabled = 0
            else:
                no_motion_cnt = no_motion_cnt + 1
        # Pretend we wrote all the bytes of s
        return len(s)

with picamera.PiCamera() as camera:
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(motion_detected_led, GPIO.OUT)
    GPIO.setup(pir_motion_detected_led, GPIO.OUT)
    GPIO.setup(pir_out, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
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
    GPIO.output(motion_detected_led, GPIO.LOW)
    GPIO.output(pir_motion_detected_led, GPIO.LOW)
    GPIO.cleanup()
