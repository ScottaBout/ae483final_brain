from flask import Flask, request, Response
import requests
import logging

from drone_data import DroneData

OPTITRACK = False # if false, assumes opti-track data equals drone data

app = Flask(__name__)

drone_data_list = [DroneData(), DroneData()]  # global variable
drone_data_list[0].ip = '192.168.1.157'  # TODO change ip address to drone address
drone_data_list[1].ip = '10.194.94.228'  # TODO change ip address to drone address

@app.route("/drone_data")
def drone_data():
    """
    Extract the drone_data x, y and z from the http request, sent to here
    by the Drone Client
    """
    drone_id = int(request.args.get("drone_id"))
    if drone_id is None:
        logging.error('Missing drone_id')
        return Response('Missing drone_id', 500)
    logging.info(f'/drone_data for drone_id {drone_id}')
    if 'x' in request.args:
        x = request.args.get('x')
        drone_data_list[drone_id].x = x
        if not OPTITRACK:
            drone_data_list[drone_id].opti_x = x
            if drone_data_list[drone_id].start_x is None:
                drone_data_list[drone_id].start_x = x
    if 'y' in request.args:
        y = request.args.get('y')
        drone_data_list[drone_id].y = y
        if not OPTITRACK:
            drone_data_list[drone_id].opti_y = y
            if drone_data_list[drone_id].start_y is None:
                drone_data_list[drone_id].start_y = y
    if 'z' in request.args:
        z = request.args.get('z')
        drone_data_list[drone_id].z = z
        if not OPTITRACK:
            drone_data_list[drone_id].opti_z = z
            if drone_data_list[drone_id].start_z is None:
                drone_data_list[drone_id].start_z = z
    response = f'Drone: {drone_id} : {drone_data_list[drone_id].x}, {drone_data_list[drone_id].y}, {drone_data_list[drone_id].z} '
    logging.info(response)
    recalculate()
    return Response(response)


def recalculate():
    """
    Based on drone_data from both drones, recalculate target drone
    positions and send to both drones
    """
    drone0 = drone_data_list[0]
    drone1 = drone_data_list[1]
    if drone0.start_x is None or drone1.start_x is None:
        logging.info('start_x not yet set for both drones')
        return
    if drone0.real_z() < 0.5:
        logging.info('Drone 0 climbing')
        drone0.set_target(drone0.start_x, drone0.start_y, 1)
    if drone1.real_z() < 0.5:
        drone1.set_target(drone1.start_x, drone1.start_y, 1)
        logging.info('Drone 1 climbing')
    if drone0.real_z() > 0.75 and drone1.real_z() > 0.75:
        logging.info('Both drones at altitude')
        drone0.set_target(3, 5, 1)
        h = drone0.heading(drone1)
        x, y = drone0.relative(2, h)
        drone1.set_target(x, y, 1)
    send_to_drone(drone0)
    send_to_drone(drone1)


def send_to_drone(drone_data: DroneData):
    """
    Send drone data to drone
    :param drone_data:
    """
    if drone_data.ip != '':
        try:
            response = requests.get(f'http://{drone_data.ip}:8080/drone_target', params=drone_data.string_dict())
            if response.status_code != 200:
                logging.warning(f'Error code sending request {response.status_code}')
            else:
                logging.info(f'Sent drone data to url: {response.url}')
                logging.info(f'- Drone data: {drone_data.string_dict()}')
                logging.info(f'- Response: {response.content}')
        except requests.exceptions.RequestException as err:
            logging.info(f'Error while receiving: {err}')
    else:
        logging.warning('No IP address set for drone, cannot send data')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app.run(host='0.0.0.0', port=8080, debug=True)
