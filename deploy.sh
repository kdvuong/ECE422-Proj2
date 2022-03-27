#!/bin/bash

sudo docker stack rm ece422
sudo docker build ./docker-images/autoscaler -t autoscaler
sudo docker stack deploy --compose-file docker-compose.yml ece422