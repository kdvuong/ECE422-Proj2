
"""
A simple web application; return the number of time it has been visited and also the amount of time that took to
run the difficult function.
"""

from flask import Flask
from redis import Redis
import random
import time

app = Flask(__name__)
redis = Redis(host='redis', port=6379)
counter = 0


def difficult_function():
    output = 1
    t0 = time.time()
    # difficulty = random.randint(1000000, 2000000)
    difficulty = 1500000
    for i in range(difficulty):
        output = output * difficulty
        output = output / (difficulty - 1)
    t1 = time.time()
    compute_time = t1 - t0
    return compute_time


@app.route('/')
def hello():
    global counter
    counter += 1
    count = redis.incr('hits')
    # time.sleep(5)
    computation_time = difficult_function()
    return 'Hello There! I have been seen {} times. I have solved the problem in {} seconds.\n'.format(counter,
                                                                                                       computation_time)


@app.route('/health')
def health_check():
    return "Healthy"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)
