#!/bin/sh

#Make a post request to kinesis_rtsp
curl -X POST -H "Content-Type: application/json" -d '{}' http://kinesisrtsp:8080/trigger

#Wait for a SIGINT and exit the program
trap "exit" INT

while true; do
    sleep 1
done
