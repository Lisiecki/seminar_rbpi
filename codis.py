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
HEARTBEAT_MSG = 0xb
REMOVE_FROM_CODIS_MSG = 0xc

UDP_IP = "<broadcast>"
UDP_PORT = 58333
MOTION_DETECTED_MSG = bytes([INTRUDER_MSG])
PIR_DETECTED_MSG = bytes([0x2])
PIR_GPIO = 7
MOTION_DETECTED_THRESHOLD = 10
INTRUDER_DETECTED_THRESHOLD = 25
MAX_NO_MOTION_CNT = 50
TIMEOUT = 5.0
COORDINATOR_PERIOD = 90.0
MOTION_THRESHOLD = 3.0
NO_MOTION_THRESHOLD = 30.0
LAST_INTRUDER_THRESHOLD = 3.0
HEARTBEAT_INTERVAL = 12.0
MAX_NO_HEARTBEATS = 3
 
no_heartbeats = 0
last_heartbeat = 0.0
last_heartbeat_from_successor = 0.0
motion_flag = False
coordinator = 0
codis_list = []
codis_list_size = 0
codis_list_pos = 0
no_motion_cnt = 0
camera_enabled = 0
pir_enabled = 0
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
        global server_socket
        global motion_flag
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
            no_motion_cnt = 0
            motion_flag = True
        else:
            if no_motion_cnt == MAX_NO_MOTION_CNT:
                motion_flag = False
            else:
                no_motion_cnt = no_motion_cnt + 1
        # Pretend we wrote all the bytes of s
        return len(s)

def motion(pin):
    if motion_flag:
        if is_coordinator == 1:
            for pi in codis_list:
                if pi != server_address:
                    intruder_msg = bytes([INTRUDER_MSG, codis_list_pos, codis_list_size])
                    server_socket.sendto(intruder_msg, pi)
            if motion_flag or codis_list_size == 1:
                print("send intruder message to all devices")
                intruder_alert()
        else:
            print("send intruder message to coordinator")
            intruder_detected(coordinator)
    return

def enable_pir():
    global pir_enabled
    if pir_enabled == 0:
        pir_enabled = 1
        GPIO.add_event_detect(PIR_GPIO, GPIO.RISING)
        GPIO.add_event_callback(PIR_GPIO, motion)

def disable_pir():
    global pir_enabled
    GPIO.remove_event_detect(PIR_GPIO)
    pir_enabled = 0

def remove_alert():
    global is_alert
    is_alert = 0
    if is_coordinator == 0:
        disable_pir()

def remove_coordinator():
    global is_coordinator
    is_coordinator = 0
    if is_alert == 0:
        disable_pir()

def set_alert():
    global is_alert
    is_alert = 1
    if is_coordinator == 0:
        enable_pir()

def set_coordinator():
    global is_coordinator
    is_coordinator = 1
    coordinator_msg = bytes([COORDINATOR_MSG, codis_list_pos, codis_list_size])
    server_socket.sendto(coordinator_msg, (UDP_IP, UDP_PORT))
    if is_alert == 0:
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
        successor_pos = 0
    while True:
        election_msg = bytes([ELECTION_MSG, codis_list_pos, codis_list_size])
        server_socket.sendto(election_msg, codis_list[successor_pos])
        try:
            remote_cmd, remote_addr = server_socket.recvfrom(5)
            if remote_cmd[MSG_INDEX_CMD] == COORDINATOR_MSG:
                if remote_cmd[MSG_INDEX_POS] != codis_list_pos:
                    print(remote_cmd, " has become the new coordinator")
                    coordinator = remote_cmd[MSG_INDEX_POS]
                    break
        except (socket.timeout):
            no_heartbeats += 1
            if no_heartbeats == MAX_NO_HEARTBEATS:
                remove_successor(successor_pos)
                codis_list.pop(remote_cmd[successor_pos])
                codis_list_size -= 1
                if successor_pos < codis_list_pos:
                    codis_list_pos -= 1
                no_heartbeats = 0
                successor_pos -= 1

def heartbeat(pos):
    heartbeat_msg = bytes([HEARTBEAT_MSG, codis_list_pos, codis_list_size])
    server_socket.sendto(heartbeat_msg, codis_list[pos])

def remove_successor(pos):
    remove_msg = bytes([HEARTBEAT_MSG, codis_list_pos, pos])
    server_socket.sendto(remove_msg, (UDP_IP, UDP_PORT))

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
                    print("received join response")
                    if codis_list_size == 0:
                        for i in range(remote_cmd[MSG_INDEX_OTHER] - 1):
                            codis_list.append(remote_addr)
                    codis_list.insert(remote_cmd[MSG_INDEX_POS], remote_addr)
                    codis_list_pos += 1
                    codis_list_size += 1
                    join(remote_addr)
                    if codis_list_size == remote_cmd[MSG_INDEX_OTHER]:
                        print("join codis system")
                        last_heartbeat_from_successor = time.time()
                        break
            except (socket.timeout):
                break

        codis_list_pos = codis_list_size
        codis_list.append(server_address)
        codis_list_size += 1
        if codis_list_size == 1:
            print("become first coordinator")
            set_coordinator()
            coordinator = codis_list_pos
            if camera_enabled == 0:
                camera_enabled = 1
                camera.start_recording(
                    # Throw away the video data, but make sure we're using H.264
                    '/dev/null', format='h264',
                    # Record motion data to our custom output object
                    motion_output=MotionDetector(camera)
                    )
        new_election_time = time.time() + COORDINATOR_PERIOD
        last_heartbeat = time.time()
        while 1:
            try:
                if (is_coordinator == 1) and (time.time() >= new_election_time):
                    new_election_time = time.time() + COORDINATOR_PERIOD
                    if codis_list_size > 1:
                        print("send election message")
                        election()
                        remove_coordinator()
                        if camera_enabled == 1:
                            camera.stop_recording()
                            camera_enabled = 0
                if (is_alert == 1) and (time.time() - last_intruder_detected) >= NO_MOTION_THRESHOLD and (time.time() - last_intruder_by_another) >= NO_MOTION_THRESHOLD:
                    print("stop alert state")
                    remove_alert()
                    if camera_enabled == 1:
                        camera.stop_recording()
                        camera_enabled = 0
                if (codis_list_size > 1) and (time.time() - last_heartbeat) > HEARTBEAT_INTERVAL:
                    print("send heartbeat to predecessor")
                    successor_pos = codis_list_pos - 1
                    if successor_pos < 0:
                        successor_pos = codis_list_size - 1
                    heartbeat(successor_pos)
                    last_heartbeat = time.time()
                    if (time.time() - last_heartbeat_from_successor) > HEARTBEAT_INTERVAL:
                        no_heartbeats += 0
                    if no_heartbeats == MAX_NO_HEARTBEATS:
                        print("remove successor from codis system")
                        remove(successor_pos)
                        codis_list.pop(remote_cmd[successor_pos])
                        codis_list_size -= 1
                        if successor_pos < codis_list_pos:
                            codis_list_pos -= 1
                        if coordinator == successor_pos:
                            set_coordinator()
                            if camera_enabled == 0:
                                camera_enabled = 1
                                camera.start_recording(
                                    # Throw away the video data, but make sure we're using H.264
                                    '/dev/null', format='h264',
                                    # Record motion data to our custom output object
                                    motion_output=MotionDetector(camera)
                                    )
                            new_election_time = time.time() + COORDINATOR_PERIOD
                remote_cmd, remote_addr = server_socket.recvfrom(5)
                if remote_cmd[MSG_INDEX_CMD] == COORDINATOR_MSG:
                    if remote_cmd[MSG_INDEX_POS] != codis_list_pos:
                        print(remote_cmd, " has become the new coordinator")
                        coordinator = remote_cmd[MSG_INDEX_POS]
                        if is_coordinator == 1:
                            remove_coordinator()
                            if camera_enabled == 1:
                                camera.stop_recording()
                                camera_enabled = 0
                elif remote_cmd[MSG_INDEX_CMD] == HEARTBEAT_MSG:
                    print("received heartbeat message from successor ")
                    last_heartbeat_from_successor = time.time()
                elif remote_cmd[MSG_INDEX_CMD] == ELECTION_MSG:
                    if remote_cmd[MSG_INDEX_POS] != codis_list_pos:
                        print("received election message")
                        set_coordinator()
                        if camera_enabled == 0:
                            camera_enabled = 1
                            camera.start_recording(
                                # Throw away the video data, but make sure we're using H.264
                                '/dev/null', format='h264',
                                # Record motion data to our custom output object
                                motion_output=MotionDetector(camera)
                                )
                        new_election_time = time.time() + COORDINATOR_PERIOD
                elif remote_cmd[MSG_INDEX_CMD] == INTRUDER_MSG:
                    if remote_cmd[MSG_INDEX_POS] != codis_list_pos:
                        last_intruder_by_another = time.time()
                        if (is_alert == 0):
                            print("start alert state")
                            set_alert()
                            if camera_enabled == 0:
                                camera_enabled = 1
                                camera.start_recording(
                                    # Throw away the video data, but make sure we're using H.264
                                    '/dev/null', format='h264',
                                    # Record motion data to our custom output object
                                    motion_output=MotionDetector(camera)
                                    )
                elif remote_cmd[MSG_INDEX_CMD] == JOIN_MSG:
                    print(remote_addr[0], " joined the codis system")
                    codis_list.append(remote_addr)
                    codis_list_size += 1
                    if remote_cmd[MSG_INDEX_POS] == (codis_list_pos + 1):
                        last_heartbeat_from_successor = time.time()
                elif remote_cmd[MSG_INDEX_CMD] == LEAVE_MSG:
                    print(remote_addr[0], " left the codis system")
                    codis_list.remove(remote_addr)
                    codis_list_size -= 1
                    if remote_cmd[MSG_INDEX_POS] < codis_list_pos:
                        codis_list_pos -= 1
                elif remote_cmd[MSG_INDEX_CMD] == JOIN_REQUEST_MSG:
                    print("received join request")
                    time.sleep(codis_list_pos * 0.5)
                    join_response(remote_addr)
                elif remote_cmd[MSG_INDEX_CMD] == REMOVE_FROM_CODIS_MSG:
                    print("received remove from codis message")
                    codis_list.pop(remote_cmd[MSG_INDEX_OTHER])
                    codis_list_size -= 1
                    if remote_cmd[MSG_INDEX_OTHER] < codis_list_pos:
                        codis_list_pos -= 1
                elif remote_cmd[MSG_INDEX_CMD] == STATUS_MSG:
                    print(remote_addr[0], " requested current status")
                    print("codis pos: ", codis_list_pos, '\n', "codis size: ", codis_list_size, '\n', "coordinator: ", is_coordinator, '\n', "alert: ", is_alert)
            except (socket.timeout):
                continue
    except KeyboardInterrupt:
        leave()
        disable_pir()
        if camera_enabled == 1:
            camera.stop_recording()
        server_socket.close()
        GPIO.cleanup()

    leave()
    disable_pir()
    if camera_enabled == 1:
        camera.stop_recording()
    server_socket.close()
    GPIO.cleanup()
