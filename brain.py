import socket
import struct
import threading

import matplotlib.colors
import matplotlib.pyplot as plt
from typing import Callable

import logging

from drone_data import DroneData

LOGLEVEL = logging.DEBUG
ONEDRONE = True  # change to FALSE when working with drones

UDP_PORT = 1234  # random number

HOVER_Z_THRESHOLD = 0.5
HOVER_Z = HOVER_Z_THRESHOLD * 1.1  # with safety margin
DRONE1_X_OFFSET = 0.5  # relative to Drone 0 at start
DRONE1_Y_OFFSET = 0  # relative to Drone 0 at start

drone_data_list = [DroneData(), DroneData()]  # global variable

drone_data_list[0].ip = '10.183.5.60'  # TODO change ip address to drone address
drone_data_list[1].ip = '10.183.5.60'  # TODO change ip address to drone address
BRAIN_PORT = '8100'
CLIENT0_PORT = '8080'
CLIENT1_PORT = '8000'
COLORS = ['r', 'g']
tracks = [[], []]  # (x,y,z, color) as a list for each drone


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
                    (drone_id, x, y, z) = struct.unpack('ifff', data)  # convert the received data from bytes to float
                    logging.info(f'Incoming = {(drone_id, x, y, z)}')
                    drone_data = drone_data_list[drone_id]
                    drone_data.x = x
                    drone_data.y = y
                    drone_data.z = z
                    if drone_data.start_x is None:
                        drone_data.start_x = x
                        drone_data.start_y = y
                        drone_data.start_z = z
                    log_drone_positions()
                    recalculate(wrap_up())
                    if wrap_up():
                        break
                else:
                    logging.warning(f'Received only {len(data)} bytes: {data}')
    logging.info('Socket listener finished')


def log_drone_positions():
    for i in range(2):
        x_offset = DRONE1_X_OFFSET if i == 1 else 0  # logging real position
        y_offset = DRONE1_Y_OFFSET if i == 1 else 0  # logging real position
        drone = drone_data_list[i]
        tracks[i].append((drone.real_x() + x_offset,
                          drone.real_y() + y_offset,
                          drone.real_z(), COLORS[i]))


def recalculate(wrap_up: bool):
    logging.debug(f'Starting recalculate, wrap_up={wrap_up}')
    drone0 = drone_data_list[0]
    drone1 = drone_data_list[1] if not ONEDRONE else drone0
    if drone0.start_x is None or drone1.start_x is None:
        logging.warning('start_x not set yet - returning from recalculate')
        return
    if drone0.real_z() < HOVER_Z_THRESHOLD:
        logging.info('setting take-off for drone 0')
        drone0.set_target(drone0.start_x, drone0.start_y, HOVER_Z)
    if drone1.real_z() < HOVER_Z_THRESHOLD:
        logging.info('setting take-off for drone 1')
        drone1.set_target(drone1.start_x, drone1.start_y, HOVER_Z)
    if drone0.real_z() > HOVER_Z_THRESHOLD and drone1.real_z() > HOVER_Z_THRESHOLD:
        set_targets_for_square_mirror(drone0, drone1)
    if wrap_up:
        # send negative target z to land the drone
        drone0.target_z = -1.0
        drone1.target_z = -1.0
    send_to_drone(drone0, 0)
    send_to_drone(drone1, 1)


def set_targets_for_square_mirror(drone0, drone1):
    """
    Simple  mirror
    """
    logging.info('Setting square mirror target for both drones')
    set_target_for_square(drone0)
    drone1.set_target(drone0.target_x, drone0.target_y, drone0.target_z)

target_quadrant = 0

def set_target_for_square(drone: DroneData):
    """
    Set square flight path for this drone
    :param drone:
    """
    assert drone.real_z() > HOVER_Z_THRESHOLD
    global target_quadrant
    radius = 1  # drone will fly to corners of (radius, radius) square
    setpoint = radius * 1.3  # drone will fly beyond those corners
    x = drone.real_x()
    y = drone.real_y()
    # quadrant is 0, 1, 2, 3 from top right clockwise
    current_quadrant = 0 if x > 0 and y > 0 else (1 if x > 0 and y <= 0 else (2 if x <= 0 and y <= 0 else 3))
    inside_square = abs(x) < radius and abs(y) < radius
    at_corner = abs(x) > (radius + setpoint) / 2 and abs(y) > (radius + setpoint) / 2
    if at_corner:
        target_quadrant = (current_quadrant + 1) % 4
        logging.info(f'At corner of quadrant {current_quadrant} moving to {target_quadrant}')
    if inside_square:
        # initially, move to corner of quadrant 0
        target_quadrant = 0
    xy = [(setpoint, setpoint), (setpoint, -setpoint), (-setpoint, -setpoint), (-setpoint, setpoint)]
    target_xy = xy[target_quadrant]
    drone.set_target(target_xy[0], target_xy[1], HOVER_Z)


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
    # plot both tracks on one map
    xs = []
    ys = []
    zs = []
    cs = []
    for i in range(2):
        xs.extend([item[0] for item in tracks[i]])
        ys.extend([item[1] for item in tracks[i]])

        # zs = ([item[2] for item in tracks[i]])
        cs.extend([item[3] for item in tracks[i]])
    plt.scatter(xs, ys, c=cs, alpha=0.8)
    plt.show()
    # print(tracks)
    # print(xs)
    # print(ys)
    # print(cs)


if __name__ == '__main__':
    main()