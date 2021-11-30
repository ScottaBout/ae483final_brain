from flask import Flask, request, Response
import requests
import logging

from drone_data import DroneData

OPTITRACK = False

app = Flask(__name__)

drone_data_list = [DroneData(), DroneData()]  # global variable


@app.route("/drone_data")
def drone_data():
    drone_id = int(request.args.get("drone_id"))
    drone_data_list[0].ip = '192.168.1.157'
    drone_data_list[1].ip = '192.168.1.158'
    payload = {}
    for v in ['x', 'y', 'z']:
        value = request.args.get(v)
        if value is not None:
            payload[v] = float(value)
    if 'x' in payload:
        drone_data_list[drone_id].x = payload['x']
        if not OPTITRACK:
            drone_data_list[drone_id].opti_x = payload['x']
            if drone_data_list[drone_id].start_x is None:  # TODO DELETE WITH OPTITRACK
                drone_data_list[drone_id].start_x = payload['x']
    if 'y' in payload:
        drone_data_list[drone_id].y = payload['y']
        if not OPTITRACK:
            drone_data_list[drone_id].opti_y = payload['y']
            if drone_data_list[drone_id].start_y is None:  # TODO DELETE WITH OPTITRACK
                drone_data_list[drone_id].start_y = payload['y']
    if 'z' in payload:
        drone_data_list[drone_id].z = payload['z']
        if not OPTITRACK:
            drone_data_list[drone_id].opti_z = payload['z']
            if drone_data_list[drone_id].start_z is None:  # TODO DELETE WITH OPTITRACK
                drone_data_list[drone_id].start_z = payload['z']

    response = f'Drone: {drone_id} : {drone_data_list[drone_id].x}, {drone_data_list[drone_id].y}, {drone_data_list[drone_id].z} '
    print(response)
    recalculate()
    return Response(response)


def recalculate():
    drone0 = drone_data_list[0]
    drone1 = drone_data_list[1]
    if drone0.start_x is None or drone1.start_x is None:
        return
    if drone0.real_z() < 0.5:
        drone0.set_target(drone0.start_x, drone0.start_y, 1)
    if drone1.real_z() < 0.5:
        drone1.set_target(drone1.start_x, drone1.start_y, 1)
    if drone0.real_z() > 0.75 and drone1.real_z() > 0.75:
        drone0.set_target(3, 5, 1)
        h = drone0.heading(drone1)
        x, y = drone0.relative(2, h)
        drone1.set_target(x, y, 1)
    send_to_drone(drone0)
    send_to_drone(drone1)


def send_to_drone(drone_data: DroneData):
    """
    Send target positioning data to drone with drone_id integer
    :param drone_data:
    :return:
    """
    if drone_data.ip != '':
        try:
            response = requests.get(f'http://{drone_data.ip}:8080/drone_target', params=drone_data.string_dict())
            if response.status_code != 200:
                print(f'Error code sending request {response.status_code}')
            else:
                print(f'url: {response.url}')
                print(f'response: {response.content}')
        except requests.exceptions.RequestException:
            logging.info('catch error while receiving')
    else:
        print("No IP address yet")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
