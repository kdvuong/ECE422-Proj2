from datetime import datetime
from typing import cast
import docker
import time
import os
from docker.models.services import Service
from flask import Flask, send_file

from flask_socketio import SocketIO, emit

client = docker.from_env()
nginx_log_path = "./logs/web.response_time.log"
period = int(os.getenv("PERIOD", 20))  # polling period (secs)
response_time_upper_threshold = int(os.getenv("UPPER_THRESHOLD", 5))
response_time_lower_threshold = int(os.getenv("LOWER_THRESHOLD", 2))
min_replica = int(os.getenv("MIN_REPLICA", 1))
max_replica = int(os.getenv("MAX_REPLICA", 3))

active = False
replicas = []
app = Flask(__name__)
socketio = SocketIO(app)

workload = [0] * 10
response_time = [0] * 10
replicas = [0] * 10
plot_period = 10

prev_response_update_ts = datetime.today()
prev_workload_update_ts = datetime.today()

@socketio.on('getPlotData')
def get_plot_data():
    emit("plotData", (workload, response_time, replicas))

def generate_plot_data():
    while True:
        start = datetime.now()
        workload_data(start)
        response_time_data(start)
        time.sleep(plot_period)

@app.route("/")
def index():
    return send_file('index.html')

@app.route("/toggle-autoscale")
def toggle():
    global active
    active = not active
    if active:
        return "autoscaler is now active"
    else:
        return "autoscaler is now NOT active"

def generate_time_ranges(start):
    last_minute = start.timestamp() - start.second
    res = []
    if last_minute == start.timestamp():
        for i in range(10, 0, -1):
            res.append(last_minute - 60 * i)
        res.append(last_minute)
    else:
        for i in range(9, 0, -1):
            res.append(last_minute - 60 * i)
        res.append(last_minute)
        res.append(start.timestamp())
    return res

def workload_data(start):
    global prev_workload_update_ts
    times = []

    with open(nginx_log_path) as f:
        for line in f.readlines():
            log_time, r = line.split()
            if float(log_time) > prev_workload_update_ts.timestamp():
                times.append(float(log_time))

    if start.minute > prev_workload_update_ts.minute:
        workload.append(len(times)/60)
        workload.pop(0)
        prev_workload_update_ts = start
    else:
        workload[-1] = len(times)/ (start.timestamp() - prev_workload_update_ts.timestamp())

def response_time_data(start):
    global prev_response_update_ts
    times = []

    with open(nginx_log_path) as f:
        for line in f.readlines():
            log_time, r = line.split()
            if float(log_time) > prev_response_update_ts.timestamp():
                times.append(float(r))

    if start.minute > prev_response_update_ts.minute:
        if len(times) > 0:
            response_time.append(sum(times)/len(times))
        else:
            response_time.append(0)
        response_time.pop(0)
        prev_response_update_ts = start
    elif len(times) > 0:
        response_time[-1] = sum(times)/len(times)

def generate_replica_data():
    while True:
        _, current_replica = get_service_and_replica()
        replicas.append(current_replica)
        if len(replicas) > 10:
            replicas.pop(0)
        time.sleep(60)

def get_service_and_replica() -> tuple[Service, int]:
    service = cast(Service, client.services.list(
        filters={"name": "ece422_web"})[0])
    return (
        service,
        int(service.attrs["Spec"]["Mode"]["Replicated"]["Replicas"])
    )


def scale_service(service, replica):
    replica = max(min_replica, int(replica))
    replica = min(max_replica, int(replica))
    service.scale(replica)

def run():
    while True:
        start = time.time()
        print(f"start: {start}")
        time.sleep(period)
        
        if active:
            times = []
            with open(nginx_log_path) as f:
                for line in f.readlines():
                    log_time, response_time = line.split()
                    if float(log_time) > start:
                        times.append(float(response_time))

            avg_response_time = 0
            if len(times):
                avg_response_time = sum(times)/len(times)
            print(f"average response time: {avg_response_time}")

            service, current_replica = get_service_and_replica()
            if avg_response_time > response_time_upper_threshold:
                print(f"scale up to {current_replica * 2}")
                current_replica = scale_service(service, current_replica * 2)
            elif avg_response_time < response_time_lower_threshold:
                print(f"scale down to {current_replica / 2}")
                current_replica = scale_service(service, int(current_replica / 2))

if __name__ == "__main__":
    import threading
    log_listener = threading.Thread(target=run)
    log_listener.start()
    plot_generator = threading.Thread(target=generate_plot_data)
    plot_generator.start()
    replica_data_generator = threading.Thread(target=generate_replica_data)
    replica_data_generator.start()
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8001)), debug=True)
