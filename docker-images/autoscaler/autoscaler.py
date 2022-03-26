from typing import List, Union, cast
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

workload = []
response_time = []
replicas = []
plot_period = 10

@socketio.on('getPlotData')
def get_plot_data():
    emit("plotData", (workload, response_time, replicas))

def generate_plot_data():
    global workload, response_time, replica
    while True:
        start = time.time()
        workload = workload_data(start)
        response_time = response_time_data(start)
        time.sleep(plot_period)

@app.route("/")
def index():
    return send_file('index.html')

@app.route("/toggle-autoscale")
def toggle():
    if active:
        active = False
    else:
        active = True
    return 200

def workload_data(start):
    times = []
    res = []
    TEN_MINUTES_AGO = start - 600
    with open(nginx_log_path) as f:
        for line in f.readlines():
            log_time, response_time = line.split()
            if float(log_time) > TEN_MINUTES_AGO:
                times.append(float(response_time))
    for i in range(0, 10):
        per_min = []
        for t in times:
            if t > TEN_MINUTES_AGO + 60 * i:
                per_min.append(t)
        if len(per_min) > 0:
            res.append(len(per_min)/60)
        else:
            res.append(0)
    return res

def response_time_data(start):
    times = []
    res = []
    TEN_MINUTES_AGO = start - 600
    with open(nginx_log_path) as f:
        for line in f.readlines():
            log_time, response_time = line.split()
            if float(log_time) > TEN_MINUTES_AGO:
                times.append(float(response_time))
    for i in range(0, 10):
        per_min = []
        for t in times:
            if t > TEN_MINUTES_AGO + 60 * i:
                per_min.append(t)
        if len(per_min) > 0:
            res.append(sum(per_min)/len(per_min))
        else:
            res.append(0)
    return res

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
    socketio.run(app, port=os.getenv("PORT", 8080))
