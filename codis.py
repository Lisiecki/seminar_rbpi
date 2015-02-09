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

ALERTED_STATE = 0x0
COORDINATOR_STATE = 0x1
INACTIVE_STATE = 0x2

SHUTDOWN_CAM_MSG = 0x0
INTRUDER_MSG = 0x1
JOIN_RESPONSE_MSG = 0x2
PAUSE_CAM_MSG = 0x3
JOIN_MSG = 0x4
LEAVE_MSG = 0x5
JOIN_REQUEST_MSG = 0x6
STATUS_MSG = 0x7
ELECTION_MSG = 0x8
COORDINATOR_MSG = 0x9
MSG_INTRUDER = 0xa

UDP_IP = "<broadcast>"
UDP_PORT = 58333
MOTION_DETECTED_MSG = bytes([INTRUDER_MSG])
PIR_DETECTED_MSG = bytes([0x2])
PIR_GPIO = 7
MOTION_DETECTED_THRESHOLD = 10
INTRUDER_DETECTED_THRESHOLD = 25
MAX_NO_MOTION_CNT = 10
TIMEOUT = 5.0
COORDINATOR_PERIOD = 15.0
MOTION_THRESHOLD = 3.0
NO_MOTION_THRESHOLD = 5.0

coordinator = 0
codis_list = []
codis_list_size = 0
codis_list_pos = 0
motion_cnt = 0
no_motion_cnt = 0
pir_enabled = 0
camera_enabled = 0
last_motion_detected = 0.0
last_intruder_detected = 0.0
last_intruder_by_another = 0.0
is_alert = 0
is_coordinator = 0

# prepares the server socket to receive data from Codis system
server_address = ("", UDP_PORT)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)   
server_socket.bind(server_address)
server_socket.settimeout(5.0)

class MotionDetector(object):

    def __init__(self, camera):
        width, height = camera.resolution
        self.cols = (width + 15) // 16
        self.cols += 1 # there's always an extra column
        self.rows = (height + 15) // 16

    def write(self, s):
        global no_motion_cnt
        global pir_enabled
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
                last_motion_detected = time.time()
        else:
            if no_motion_cnt == MAX_NO_MOTION_CNT:
                motion_cnt = 0
            else:
                no_motion_cnt = no_motion_cnt + 1
        # Pretend we wrote all the bytes of s
        return len(s)

def motion(pin):
    if (time.time() - last_motion_detected) <= MOTION_THRESHOLD:
        if coordinator == codis_list_pos:
            print("intruder alert")
            intruder_alert()
        else:
            print("intruder detected")
            intruder_detected(coordinator)
    return

def enable_camera(camera):
    global camera_enabled
    if camera_enabled == 0:
        camera.start_recording(
            # Throw away the video data, but make sure we're using H.264
            '/dev/null', format='h264',
            # Record motion data to our custom output object
            motion_output=MotionDetector(camera)
            )
        camera_enabled = 1

def enable_pir():
    global pir_enabled
    if pir_enabled == 0:
        pir_enabled = 1
        GPIO.add_event_detect(PIR_GPIO, GPIO.RISING)
        GPIO.add_event_callback(PIR_GPIO, motion)

def disable_camera(camera):
    try:
        _check_camera_open()
        camera.stop_recording()
    except:
        print("exception")

def disable_pir():
    global pir_enabled
    GPIO.remove_event_detect(PIR_GPIO)
    pir_enabled = 0

def remove_alert(camera):
    global is_alert
    is_alert = 0
    if is_coordinator == 0:
        disable_pir()
        disable_camera(camera)

def remove_coordinator(camera):
    global is_coordinator
    is_coordinator = 0
    if is_alert == 0:
        disable_pir()
        disable_camera(camera)

def set_alert(camera):
    global is_alert
    is_alert = 1
    if is_coordinator == 0:
        enable_camera(camera)
        enable_pir()

def set_coordinator(camera):
    global is_coordinator
    is_coordinator = 1
    coordinator_msg = bytes([COORDINATOR_MSG, codis_list_pos, codis_list_size])
    server_socket.sendto(coordinator_msg, (UDP_IP, UDP_PORT))
    if is_alert == 0:
        enable_camera(camera)
        enable_pir()

def join_response(addr):
    join_response_msg = bytes([JOIN_RESPONSE_MSG, codis_list_pos, codis_list_size])
    server_socket.sendto(join_response_msg, addr)

def request_join():
    join_msg = bytes([JOIN_REQUEST_MSG, codis_list_pos, codis_list_size])
    server_socket.sendto(join_msg, (UDP_IP, UDP_PORT))

def join(addr):
    join_msg = bytes([JOIN_MSG, codis_list_pos, codis_list_size])
    server_socket.sendto(join_msg, addr)

def leave():
    leave_msg = bytes([LEAVE_MSG, codis_list_pos, codis_list_size])
    server_socket.sendto(leave_msg, (UDP_IP, UDP_PORT))

def intruder_alert():
    intruder_msg = bytes([INTRUDER_MSG, codis_list_pos, codis_list_size])
    server_socket.sendto(intruder_msg, (UDP_IP, UDP_PORT))

def intruder_detected(pos):
    intruder_msg = bytes([INTRUDER_MSG, codis_list_pos, codis_list_size])
    server_socket.sendto(intruder_msg, codis_list[pos])

def election():
    successor_pos = codis_list_pos + 1
    if codis_list_size == successor_pos:
        print("loop")
        successor_pos = 0
    print("size ", codis_list_size)
    print("pos ", successor_pos)
    print("successor ", codis_list[successor_pos])
    print("first ", codis_list[0])
    election_msg = bytes([ELECTION_MSG, codis_list_pos, codis_list_size])
    server_socket.sendto(election_msg, codis_list[successor_pos])

with picamera.PiCamera() as camera:
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(PIR_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    camera.resolution = (1280, 720)
    camera.framerate = 30

    try:
        request_join()
        wait = time.time() + 5.0
        while time.time() < wait:
            try:
                remote_cmd, remote_addr = server_socket.recvfrom(5)
                if remote_cmd[MSG_INDEX_CMD] == JOIN_RESPONSE_MSG:
                    print("join response")
                    if codis_list_size == 0:
                        for i in range(remote_cmd[MSG_INDEX_OTHER]):
                            codis_list.append(remote_addr)
                    codis_list.insert(remote_cmd[MSG_INDEX_POS], remote_addr)
                    codis_list_pos += 1
                    codis_list_size += 1
                    join(remote_addr)
                    if codis_list_size == remote_cmd[MSG_INDEX_OTHER]:
                        print("ready")
                        break
            except (socket.timeout):
                print("join timeout")
                break

        codis_list_pos = codis_list_size
        codis_list.append(server_address)
        codis_list_size += 1
        if codis_list_size == 1:
            print("is coordinator")
            set_coordinator(camera)
        new_election_time = time.time() + COORDINATOR_PERIOD
        while 1:
            try:
                if (is_coordinator == 1) and (time.time() >= new_election_time):
                    print("new period")
                    new_election_time = time.time() + COORDINATOR_PERIOD
                    if codis_list_size > 1:
                        print("new coordinator")
                        election()
                if (is_alert == 1) and (time.time() - last_intruder_detected) >= NO_MOTION_THRESHOLD and (time.time() - last_intruder_by_another) >= NO_MOTION_THRESHOLD:
                    print("remove alert")
                    remove_alert(camera)
                remote_cmd, remote_addr = server_socket.recvfrom(5)
                if remote_cmd[MSG_INDEX_CMD] == COORDINATOR_MSG:
                    if remote_cmd[MSG_INDEX_POS] != codis_list_pos:
                        print("coordinator")
                        if is_coordinator == 1:
                            remove_coordinator(camera)
                elif remote_cmd[MSG_INDEX_CMD] == ELECTION_MSG:
                    if remote_cmd[MSG_INDEX_POS] != codis_list_pos:
                        print("election")
                        set_coordinator(camera)
                        new_election_time = time.time() + COORDINATOR_PERIOD
                elif remote_cmd[MSG_INDEX_CMD] == INTRUDER_MSG:
                    if remote_cmd[MSG_INDEX_POS] != codis_list_pos:
                        print("intruder")
                        last_intruder_by_another = time.time()
                        if (is_alert == 0):
                            set_alert(camera)
                elif remote_cmd[MSG_INDEX_CMD] == JOIN_MSG:
                    print("join ")
                    codis_list.append(remote_addr)
                    codis_list_size += 1
                    for i in codis_list:
                        print("item ", i)
                elif remote_cmd[MSG_INDEX_CMD] == LEAVE_MSG:
                    print("leave")
                    codis_list.remove(remote_addr)
                    codis_list_size -= 1
                    if remote_cmd[MSG_INDEX_POS] < codis_list_pos:
                        codis_list_pos -= 1
                elif remote_cmd[MSG_INDEX_CMD] == JOIN_REQUEST_MSG:
                    print("join request")
                    time.sleep(codis_list_pos * 0.5)
                    join_response(remote_addr)
                elif remote_cmd[MSG_INDEX_CMD] == STATUS_MSG:
                    print("status")
                    print("codis pos: ", codis_list_pos, '\n', "codis size: ", codis_list_size)
            except (socket.timeout):
                print("main timeout")
    except KeyboardInterrupt:
        leave()
        disable_pir()
        disable_camera(camera)
        server_socket.close()
        GPIO.cleanup()

    leave()
    disable_pir()
    disable_camera(camera)
    server_socket.close()
    GPIO.cleanup()
