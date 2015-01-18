from __future__ import division
#!/usr/bin/python3

import socket
import picamera
import numpy as np
import RPi.GPIO as GPIO
import time, sys

motion_dtype = np.dtype([
    ('x', 'i1'),
    ('y', 'i1'),
    ('sad', 'u2'),
    ])

CMD_SHUTDOWN_CAM = 0x0
CMD_MOTION_DETECTED = 0x1
CMD_IDENTIFY = 0x2
CMD_PAUSE_CAM = 0x3

UDP_IP = '255.255.255.255'
UDP_PORT = 58333
MOTION_DETECTED_MSG = bytes([CMD_MOTION_DETECTED])
PIR_DETECTED_MSG = bytes([0x2])
PIR_GPIO = 7
MOTION_DETECTED_THRESHOLD = 5

motion_cnt = 0
no_motion_cnt = 0
pir_event_enabled = 0
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)   
server.bind(('192.168.0.19', UDP_PORT))

class MotionDetector(object):

    def __init__(self, camera):
        width, height = camera.resolution
        self.cols = (width + 15) // 16
        self.cols += 1 # there's always an extra column
        self.rows = (height + 15) // 16

    def motion(self, pin):
        server.sendto(PIR_DETECTED_MSG, (UDP_IP, UDP_PORT))
        return

    def write(self, s):
        global no_motion_cnt
        global pir_event_enabled
        global server
        global motion_cnt

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
            motion_cnt += 1
            no_motion_cnt = 0

            if motion_cnt == MOTION_DETECTED_THRESHOLD:
                motion_cnt = 0
                server.sendto(MOTION_DETECTED_MSG, (UDP_IP, UDP_PORT))
                if pir_event_enabled == 0:
                    pir_event_enabled = 1
                    GPIO.add_event_detect(PIR_GPIO, GPIO.RISING)
                    GPIO.add_event_callback(PIR_GPIO, self.motion)
        else:
            if no_motion_cnt == 40:
                GPIO.remove_event_detect(PIR_GPIO)
                pir_event_enabled = 0
                motion_cnt = 0
            else:
                no_motion_cnt = no_motion_cnt + 1
        # Pretend we wrote all the bytes of s
        return len(s)

with picamera.PiCamera() as camera:
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(PIR_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    camera.resolution = (640, 480)
    camera.framerate = 30
    camera.start_recording(
        # Throw away the video data, but make sure we're using H.264
        '/dev/null', format='h264',
        # Record motion data to our custom output object
        motion_output=MotionDetector(camera)
        )
    
    while 1:
        remote_cmd = server.recvfrom(1)[0]
        print(remote_cmd[0])
        if remote_cmd[0] == CMD_SHUTDOWN_CAM:
            print("break")
            break
        elif remote_cmd[0] == CMD_MOTION_DETECTED:
            if pir_event_enabled == 0:
                pir_event_enabled = 1
                GPIO.add_event_detect(PIR_GPIO, GPIO.RISING)
                GPIO.add_event_callback(PIR_GPIO, self.motion)
        elif remote_cmd[0] == CMD_IDENTIFY:
            break
        elif remote_cmd[0] == CMD_PAUSE_CAM:
            break

    camera.stop_recording()
    server.close()
    GPIO.cleanup()
