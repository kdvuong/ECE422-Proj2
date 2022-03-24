import docker
import time
import json

client = docker.from_env()

period = 10  # polling period (secs)
nginx_log_path = ""
response_time_threshold = 20
min_replica = 1
max_replica = 3


def get_log_time(s):
    return 1


def get_response_time(s):
    return 1


def get_service():
    return client.services.list(filters={"name": "ece422_web"})[0]


def run():
    while True:
        start = time.time()
        time.sleep(period)
        times = []
        with open(nginx_log_path) as f:
            for line in f.readlines():
                log_time = get_log_time(line)
                if log_time > start:
                    times.append(get_response_time(line))

        avg_response_time = sum(times)/len(times)
        if avg_response_time > response_time_threshold:
            service = get_service()
            current_replica_count = service.attrs["Spec"]["Mode"]["Replicated"]["Replicas"]
            if current_replica_count < max_replica:
                service.scale(max(current_replica_count * 2, max_replica))


if __name__ == "__main__":
    run()
