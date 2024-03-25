#!/usr/bin/bash

if [ $# -eq 0 ]
then
    echo "No arguments supplied"
    exit
fi

echo "version: '3.9'
name: tp0
services:
  server:
    container_name: server
    image: server:latest
    entrypoint: python3 /main.py
    environment:
      - PYTHONUNBUFFERED=1
      - LOGGING_LEVEL=DEBUG
    networks:
      - testing_net
    volumes:
      - ./server/config.ini:/config.ini"> temp.yaml

for (( i = 1; i <= $1; i++ )) 
do
echo "
  client$i:
    container_name: client$i
    image: client:latest
    entrypoint: /client
    environment:
      - CLI_ID=$i
      - CLI_LOG_LEVEL=DEBUG
    networks:
      - testing_net
    depends_on:
      - server
    volumes:
      - ./client/config.yaml:/config.yaml
      - ./client/agency-$i.csv:/agency-$i.csv" >> temp.yaml
done

echo "
networks:
  testing_net:
    ipam:
      driver: default
      config:
        - subnet: 172.25.125.0/24" >> temp.yaml

mv temp.yaml docker-compose-dev.yaml