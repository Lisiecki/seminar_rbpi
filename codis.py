from __future__ import division
#!/usr/bin/python3

import socket
import picamera
import numpy as np
import RPi.GPIO as GPIO
import time, sys
from socketserver import UDPServer, BaseRequestHandler

motion_dtype = np.dtype([
    ('x', 'i1'),
    ('y', 'i1'),
    ('sad', 'u2'),
    ])

MSG_INDEX_CMD = 0x0
MSG_INDEX_POS = 0x1
MSG_INDEX_OTHER = 0x2

CMD_SHUTDOWN_CAM = 0x0
CMD_MOTION_DETECTED = 0x1
CMD_IDENTIFY = 0x2
CMD_PAUSE_CAM = 0x3
CMD_JOIN_CODIS = 0x4
CMD_LEAVE_CODIS = 0x5
CMD_JOIN_REQUEST = 0x6
CMD_STATUS = 0x7
CMD_ELECTION = 0x8
CMD_COORDINATOR = 0x9

UDP_IP = "<broadcast>"
UDP_PORT = 58333
MOTION_DETECTED_MSG = bytes([CMD_MOTION_DETECTED])
PIR_DETECTED_MSG = bytes([0x2])
PIR_GPIO = 7
MOTION_DETECTED_THRESHOLD = 5
INTRUDER_DETECTED_THRESHOLD = 25

codis_list = []
codis_list_size = 0
codis_list_pos = 0
motion_cnt = 0
no_motion_cnt = 0
pir_event_enabled = 0
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)   
server_socket.bind(("", UDP_PORT))

class MotionDetector(object):

    def __init__(self, camera):
        width, height = camera.resolution
        self.cols = (width + 15) // 16
        self.cols += 1 # there's always an extra column
        self.rows = (height + 15) // 16

    def motion(self, pin):
        server_socket.sendto(PIR_DETECTED_MSG, (UDP_IP, UDP_PORT))
        return

    def write(self, s):
        global no_motion_cnt
        global pir_event_enabled
        global server_socket
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
                server_socket.sendto(MOTION_DETECTED_MSG, (UDP_IP, UDP_PORT))
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

    def enable_cam(self):
        print(2)

    def disable_cam(self):
        print(2)

class CodisHandler(BaseRequestHandler):
    def handle(self):
        if remote_cmd[MSG_INDEX_CMD] == CMD_SHUTDOWN_CAM:
            print("shutdown")
        elif remote_cmd[MSG_INDEX_CMD] == CMD_MOTION_DETECTED:
            if pir_event_enabled == 0:
                pir_event_enabled = 1
                GPIO.add_event_detect(PIR_GPIO, GPIO.RISING)
                GPIO.add_event_callback(PIR_GPIO, motion)
        elif remote_cmd[MSG_INDEX_CMD] == CMD_PAUSE_CAM:
            print("pause")
        elif remote_cmd[MSG_INDEX_CMD] == CMD_JOIN_CODIS:
            print("HEEREEREE")
        elif remote_cmd[MSG_INDEX_CMD] == CMD_LEAVE_CODIS:
            codis_list.remove(remote_addr[0])
            codis_list_size -= 1
            if remote_cmd[MSG_INDEX_POS] < codis_list_pos:
                codis_list_pos -= 1
        elif remote_cmd[MSG_INDEX_CMD] == CMD_JOIN_REQUEST:
            print("identify")
            codis_list.append(remote_addr[0])
            codis_list_size += 1
            identify(remote_addr)
        elif remote_cmd[MSG_INDEX_CMD] == CMD_STATUS:
            print("codis pos: ", codis_list_pos, '\n', "codis size: ", codis_list_size)

def motion(pin):
    server_socket.sendto(PIR_DETECTED_MSG, (UDP_IP, UDP_PORT))
    return

def identify(addr):
    identify_msg = bytes([CMD_IDENTIFY, codis_list_pos, codis_list_size])
    server_socket.sendto(identify_msg, addr)

def request_join():
    join_msg = bytes([CMD_JOIN_REQUEST, codis_list_pos, codis_list_size])
    server_socket.sendto(join_msg, (UDP_IP, UDP_PORT))

def join(addr):
    join_msg = bytes([CMD_JOIN_CODIS, codis_list_pos, codis_list_size])
    server_socket.sendto(join_msg, addr)

def leave():
    leave_msg = bytes([CMD_LEAVE_CODIS, codis_list_pos, codis_list_size])
    server_socket.sendto(leave_msg, (UDP_IP, UDP_PORT))

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
    try:
        request_join()
        wait = time.clock() + 5.0
        while time.clock() < wait:
            remote_cmd, remote_addr = server_socket.recvfrom(4)
            if remote_cmd[MSG_INDEX_CMD] == CMD_IDENTIFY:
                print("join")
                codis_list.insert(remote_cmd[MSG_INDEX_POS], remote_addr[0])
                codis_list_pos += 1
                join(remote_addr)

        codis_list_pos += 1
        codis_list.append(remote_addr[0])
        codis_list_size = codis_list_pos

        while 1:
            remote_cmd, remote_addr = server_socket.recvfrom(4)
            print(remote_cmd[MSG_INDEX_CMD])
            if remote_cmd[MSG_INDEX_CMD] == CMD_SHUTDOWN_CAM:
                break
            elif remote_cmd[MSG_INDEX_CMD] == CMD_MOTION_DETECTED:
                if pir_event_enabled == 0:
                    pir_event_enabled = 1
                    GPIO.add_event_detect(PIR_GPIO, GPIO.RISING)
                    GPIO.add_event_callback(PIR_GPIO, motion)
            elif remote_cmd[MSG_INDEX_CMD] == CMD_PAUSE_CAM:
                break
            elif remote_cmd[MSG_INDEX_CMD] == CMD_JOIN_CODIS:
                print("HEEREEREE")
            elif remote_cmd[MSG_INDEX_CMD] == CMD_LEAVE_CODIS:
                codis_list.remove(remote_addr[0])
                codis_list_size -= 1
                if remote_cmd[MSG_INDEX_POS] < codis_list_pos:
                    codis_list_pos -= 1
            elif remote_cmd[MSG_INDEX_CMD] == CMD_JOIN_REQUEST:
                print("identify")
                codis_list.append(remote_addr[0])
                codis_list_size += 1
                identify(remote_addr)
            elif remote_cmd[MSG_INDEX_CMD] == CMD_STATUS:
                print("codis pos: ", codis_list_pos, '\n', "codis size: ", codis_list_size)
    except KeyboardInterrupt:
        leave()
        camera.stop_recording()
        server_socket.close()
        GPIO.cleanup()

    leave()
    camera.stop_recording()
    server_socket.close()
    GPIO.cleanup()
