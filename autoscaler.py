from typing import List, Union, cast
import docker
import time
import json

from docker.models.services import Service

client = docker.from_env()

period = 20  # polling period (secs)
nginx_log_path = "./logs/web.response_time.log"
response_time_upper_threshold = 5
response_time_lower_threshold = 2
min_replica = 1
max_replica = 3


def get_log_time(s):
    return 1


def get_response_time(s):
    return 1


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
            scale_service(service, current_replica * 2)
        elif avg_response_time < response_time_lower_threshold:
            print(f"scale down to {current_replica / 2}")
            scale_service(service, int(current_replica / 2))


if __name__ == "__main__":
    run()
