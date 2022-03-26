from typing import List, Union, cast
import time
import json
import os
from flask import Flask, send_from_directory, send_file
import base64
from io import BytesIO

from matplotlib.figure import Figure
from flask_socketio import SocketIO, emit

nginx_log_path = "./logs/web.response_time.log"
period = os.getenv("PERIOD", 20)  # polling period (secs)
response_time_upper_threshold = os.getenv("UPPER_THRESHOLD", 5)
response_time_lower_threshold = os.getenv("LOWER_THRESHOLD", 2)
min_replica = os.getenv("MIN_REPLICA", 1)
max_replica = os.getenv("MAX_REPLICA", 3)

active = False
replicas = []
app = Flask(__name__)
socketio = SocketIO(app)

import random
@socketio.on('getPlotData')
def get_plot_data():
    # TODO
    workload= [random.randint(1,10) for i in range(5)]
    response_time= [random.randint(1,10) for i in range(5)]
    replica= [random.randint(1,10) for i in range(5)]
    print("receive from client:")
    emit("plotData", (workload, response_time, replica))

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

def workload_data():
    pass

def response_time_data(start):
    with open(nginx_log_path) as f:
        for line in f.readlines():
            log_time, response_time = line.split()
            if float(log_time) > start:
                times.append(float(response_time))

def replica_data():
    return replicas


def scale_service(service, replica):
    replica = max(min_replica, int(replica))
    replica = min(max_replica, int(replica))
    service.scale(replica)
    return replica


if __name__ == "__main__":
    import threading
    socketio.run(app, port=os.getenv("PORT", 8080))
