from flask import Flask, request, Response
import requests

from drone_data import DroneData

app = Flask(__name__)

drone_data_list = [DroneData(), DroneData()]  # global variable


@app.route("/drone_data")
def drone_data():
    drone_id = int(request.args.get("drone_id"))
    drone_data_list[drone_id].ip = request.remote_addr
    payload = {}
    for v in ['ae483log.o_x', 'ae483log.o_y', 'ae483log.o_z']:
        value = request.args.get(v)
        if value is not None:
            payload[v] = float(value)
    if 'ae483log.o_x' in payload:
        drone_data_list[drone_id].x = payload['ae483log.o_x']
    if 'ae483log.o_y' in payload:
        drone_data_list[drone_id].y = payload['ae483log.o_y']
    if 'ae483log.o_z' in payload:
        drone_data_list[drone_id].z = payload['ae483log.o_z']

    response = f'Drone: {drone_id} : {drone_data_list[drone_id].x}, {drone_data_list[drone_id].y}, {drone_data_list[drone_id].z} '
    print(response)
    recalculate()
    return Response(response)


def recalculate():
    drone0 = drone_data_list[0]
    drone1 = drone_data_list[1]
    if drone0.start_x is None or drone1.start_x is None:
        return
    if drone0.real_z() < 1:
        drone0.set_target(drone0.start_x, drone0.start_x, 2)
    if drone1.real_z() < 1:
        drone1.set_target(drone1.real_x(), drone1.real_y(), 2)
    if drone0.real_z() > 1.5 and drone1.real_z() > 1.5:
        drone0.set_target(3, drone0.real_y(), 2)
        h = drone0.heading(drone1)
        x, y = drone0.relative(2, h)
        drone1.set_target(x, y, 2)
    send_to_drone(drone0)
    send_to_drone(drone1)


def send_to_drone(drone_data: DroneData):
    """
    Send target positioning data to drone with drone_id integer
    :param drone_data:
    :return:
    """
    if drone_data.ip != '':
        response = requests.get(f'http://{drone_data.ip}:8080/drone_target', params=drone_data.string_dict())
        if response.status_code != 200:
            print(f'Error code sending request {response.status_code}')
        else:
            print(f'url: {response.url}')
            print(f'response: {response.content}')
    else:
        print("No IP address yet")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
