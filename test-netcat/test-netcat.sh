#!/bin/sh

#Creating random message
msg=$(mktemp -u XXXXXX)

#Response from server
response=$(echo $msg | nc -v server 12345)

if [ "$msg" = "$response" ]; then
    echo "Server response is correct"
else
    echo "Server response is not correct: sent $msg, received $response"
fi