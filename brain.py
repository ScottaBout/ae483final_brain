import socket
import struct
import threading
import time

from flask import Flask, request, Response
import requests
import logging

from drone_data import DroneData

OPTITRACK = False  # if false, assumes optitrack data equals drone data
ONEDRONE = True  # change to FALSE when working with drones

OPTI_IP = "192.168.1.103"  # need to be the ip address of current device
UDP_PORT = 1234  # random number

app = Flask(__name__)

drone_data_list = [DroneData(), DroneData()]  # global variable

drone_data_list[0].ip = '192.168.1.166'  # TODO change ip address to drone address
drone_data_list[1].ip = '192.168.1.166'  # TODO change ip address to drone address
BRAIN_PORT = '8100'
CLIENT_PORT = '8080'
CLIENT_PORT2 = '8000'


@app.route("/drone_data")
def drone_data():
    drone_id = int(request.args.get("drone_id"))
    if drone_id is None:
        logging.error('Missing drone_id')
        return Response('Missing drone_id', 500)
    logging.info(f'/drone_data for drone_id {drone_id}')
    if 'x' in request.args:
        x = float(request.args.get('x'))
        drone_data_list[drone_id].x = x
        if not OPTITRACK:
            drone_data_list[drone_id].opti_x = x
            if drone_data_list[drone_id].start_x is None:
                drone_data_list[drone_id].start_x = x
    if 'y' in request.args:
        y = float(request.args.get('y'))
        drone_data_list[drone_id].y = y
        if not OPTITRACK:
            drone_data_list[drone_id].opti_y = y
            if drone_data_list[drone_id].start_y is None:
                drone_data_list[drone_id].start_y = y
    if 'z' in request.args:
        z = float(request.args.get('z'))
        drone_data_list[drone_id].z = z
        if not OPTITRACK:
            drone_data_list[drone_id].opti_z = z
            if drone_data_list[drone_id].start_z is None:
                drone_data_list[drone_id].start_z = z
    logging.debug(drone_data_list[drone_id].string_dict())
    response = f'Drone: {drone_id} : ip = {drone_data_list[drone_id].ip}, x = {drone_data_list[drone_id].x}, y = {drone_data_list[drone_id].y}, z = {drone_data_list[drone_id].z} '
    logging.info(response)
    recalculate()
    return Response(response)


def recalculate():
    logging.info('Starting recalculate')
    drone0 = drone_data_list[0]
    drone1 = drone_data_list[1] if not ONEDRONE else drone0
    if drone0.start_x is None or drone1.start_x is None:
        logging.warning('start_x not set yet - returning from recalculate')
        return
    if drone0.real_z() < 0.5:
        logging.info('setting target for drone 0')
        drone0.set_target(drone0.start_x, drone0.start_y, 0.55)
    if drone1.real_z() < 0.5:
        logging.info('setting target for drone 1')
        drone1.set_target(drone1.start_x, drone1.start_y, 0.55)
    if drone0.real_z() > 0.5 and drone1.real_z() > 0.5:
        logging.info('setting target for both drones')
        drone0.set_target(1, 2, 1)
        drone1.set_target(drone0.x, drone0.y, drone0.z)
        # h = drone0.heading(drone1)
        # x, y = drone0.relative(2, h)
        # drone1.set_target(x, y, 1)
    send_to_drone(drone0, 0)
    send_to_drone(drone1, 1)


def send_to_drone(drone_data: DroneData, id):
    """
    Send target positioning data to drone with drone_id integer
    :param drone_data:
    :return:
    """
    logging.info(f'send_to_drone')
    if drone_data.ip != '':
        logging.info(f'Client IP = {drone_data.ip}')
        PORT = CLIENT_PORT if id == 0 else CLIENT_PORT2
        try:
            response = requests.get(f'http://{drone_data.ip}:{PORT}/drone_target', params=drone_data.string_dict())
            if response.status_code != 200:
                logging.warning(f'Error code sending request {response.status_code}')
            else:
                logging.info(f'Successfully sent drone_data: {drone_data}')
                logging.info(f'Client response: {response.content}')
        except (requests.exceptions.RequestException, ConnectionError) as err:
            logging.warning(f'Error sending request to Client: {err}')
    else:
        logging.warning('No Client IP address yet')


def optitrack():
    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP
    sock.bind((OPTI_IP, UDP_PORT))

    while True:
        data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
        # print("received message: %s" % data)
        [a, b, c, d, e, f, g, h] = struct.unpack('ffffffff', data)  # convert the received data from char to float
        logging.debug(f'from optitrack: {[a, b, c, d, e, f, g, h]}')
        x = -a
        y = c
        z = b
        roll = -d
        yaw = e
        pitch = -f
        bodyID = g
        framecount = h
        drone_id = int(bodyID)
        drone_data_list[drone_id].opti_x = x
        drone_data_list[drone_id].opti_y = y
        drone_data_list[drone_id].opti_z = z
        if drone_data_list[drone_id].start_x is None:
            drone_data_list[drone_id].start_x = x
        if drone_data_list[drone_id].start_y is None:
            drone_data_list[drone_id].start_y = y
        if drone_data_list[drone_id].start_z is None:
            drone_data_list[drone_id].start_z = z


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    if OPTITRACK:
        thread = threading.Thread(target=optitrack)
        thread.start()
    # while True:
    #     time.sleep(1)
    logging.info('Starting web server')
    app.run(host='0.0.0.0', port=int(BRAIN_PORT), debug=True)
