from flask import Flask, request, Response
import requests
import logging

from drone_data import DroneData

OPTITRACK = False # if false, assumes optitrack data equals drone data

app = Flask(__name__)

drone_data_list = [DroneData(), DroneData()]  # global variable

drone_data_list[0].ip = '192.168.1.157'  # TODO change ip address to drone address
drone_data_list[1].ip = '10.194.94.228'  # TODO change ip address to drone address

@app.route("/drone_data")
def drone_data():
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
    response = f'Drone: {drone_id} : ip = {drone_data_list[drone_id].ip}, x = {drone_data_list[drone_id].x}, y = {drone_data_list[drone_id].y}, z = {drone_data_list[drone_id].z} '
    logging.info(response)
    recalculate()
    print('recalculating')
    return Response(response)


def recalculate():
    print('entered recalculation')
    drone0 = drone_data_list[0]
    drone1 = drone_data_list[1]
    if drone0.start_x is None or drone1.start_x is None:
        return
    if drone0.real_z() < 0.5:
        print('setting target for drone 0')
        drone0.set_target(drone0.start_x, drone0.start_y, 0.55)
    if drone1.real_z() < 0.5:
        print('setting target for drone 1')
        drone1.set_target(drone1.start_x, drone1.start_y, 0.55)
    if drone0.real_z() > 0.5 and drone1.real_z() > 0.5:
        drone0.set_target(1, 2, 1)
        h = drone0.heading(drone1)
        x, y = drone0.relative(2, h)
        drone1.set_target(x, y, 1)
    send_to_drone(drone0)
    print('sending to drone 0')
    send_to_drone(drone1)
    print('sending to drone 1')


def send_to_drone(drone_data: DroneData):
    """
    Send target positioning data to drone with drone_id integer
    :param drone_data:
    :return:
    """
    print('send to drone activated')
    if drone_data.ip != '':
        print(f'ip found at {drone_data.ip}, trying')
        try:
            response = requests.get(f'http://{drone_data.ip}:8080/drone_target', params=drone_data.string_dict())
            if response.status_code != 200:
                print(f'Error code sending request {response.status_code}')
            else:
                print(f'url: {response.url}')
                print(f'response: {response.content}')
        except requests.exceptions.RequestException as err:
            logging.warning(f'error: {err}')
    else:
        print("No IP address yet")


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    print('running server on brain')
    app.run(host='0.0.0.0', port=8080, debug=True)
