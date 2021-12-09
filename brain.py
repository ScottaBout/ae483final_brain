import socket
import struct
import threading
# import time
from typing import Callable

# from flask import Flask, request, Response
# import requests
import logging

from drone_data import DroneData

LOGLEVEL = logging.DEBUG
ONEDRONE = True  # change to FALSE when working with drones

UDP_PORT = 1234  # random number

drone_data_list = [DroneData(), DroneData()]  # global variable

drone_data_list[0].ip = '10.193.202.198'  # TODO change ip address to drone address
drone_data_list[1].ip = '10.193.202.198'  # TODO change ip address to drone address
BRAIN_PORT = '8100'
CLIENT0_PORT = '8080'
CLIENT1_PORT = '8000'


def drone_data_listener(wrap_up: Callable[[], bool]):
    logging.basicConfig(level=LOGLEVEL)
    logging.info(f'Starting socket listener')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(('0.0.0.0', int(BRAIN_PORT)))
        logging.info(f'Socket connected and listening')
        while True:
            data = s.recvfrom(1024)[0]
            if not data:
                logging.info('No data received')
                break
            else:
                if len(data) == 16:
                    # struct contains 1 short (id) and 3 floats, representing x, y and z
                    (drone_id, x, y, z) = struct.unpack('hfff', data)  # convert the received data from bytes to float
                    logging.info(f'Incoming = {(drone_id, x, y, z)}')
                    drone_data = drone_data_list[drone_id]
                    drone_data.x = x
                    drone_data.y = y
                    drone_data.z = z
                    if drone_data.start_x is None:
                        drone_data.start_x = x
                        drone_data.start_y = y
                        drone_data.start_z = z
                    recalculate(wrap_up())
                    if wrap_up():
                        break
                else:
                    logging.warning(f'Received only {len(data)} bytes: {data}')
    logging.info('Socket listener finished')


def recalculate(wrap_up: bool):
    logging.debug(f'Starting recalculate, wrap_up={wrap_up}')
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
        drone1.set_target(drone0.target_x, drone0.target_y, drone0.target_z)
        # h = drone0.heading(drone1)
        # x, y = drone0.relative(2, h)
        # drone1.set_target(x, y, 1)
    if wrap_up:
        # send negative target z to land the drone
        drone0.target_z = -1.0
        drone1.target_z = -1.0
    send_to_drone(drone0, 0)
    send_to_drone(drone1, 1)


def send_to_drone(drone_data: DroneData, id):
    """
    Send target positioning data to drone with drone_id integer
    :param drone_data:
    :return:
    """
    logging.debug(f'send_to_drone')
    if drone_data.ip != '':
        port = CLIENT0_PORT if id == 0 else CLIENT1_PORT
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            data = struct.pack('fff', drone_data.target_x, drone_data.target_y, drone_data.target_z)
            b = s.sendto(data, (drone_data.ip, int(port)))
            logging.info(
                f'Sent {b} bytes with {(drone_data.target_x, drone_data.target_y, drone_data.target_z)} to {drone_data.ip}:{port}')
    else:
        logging.warning('No Client IP address yet')


def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.info('Starting drone_data_listener')
    wrap_up = False
    t1 = threading.Thread(target=drone_data_listener, args=(lambda: wrap_up,))
    t1.start()
    input('Press enter to end and land the drones')
    value = wrap_up = True
    t1.join()
    logging.info('Finished')


if __name__ == '__main__':
    main()