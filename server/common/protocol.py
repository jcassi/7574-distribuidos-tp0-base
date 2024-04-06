import logging
import socket
from common.utils import Bet

PAYLOAD_LEN = 2
CLIENT_ID_LEN = 1
MAX_BUFFER_SIZE = 1024

def ReceiveBet(client_sock: socket):
    bytes_read = ReadFromSocket(client_sock, CLIENT_ID_LEN + PAYLOAD_LEN)
    size = bytes_read[0] << 8 | bytes_read[1]
    client_id = int(bytes_read[2])

    bytes_read = ReadFromSocket(client_sock, size)
    msg = bytes(bytes_read).decode("utf-8")
    addr = client_sock.getpeername()
    
    fields = msg.split(',')
    if len(fields) < 5:
        logging.info(f'action: receive_message | result: fail | ip: {addr[0]} | msg: {msg}')
        return None
    else:
        logging.info(f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg}')
        return Bet(client_id, fields[0], fields[1], fields[2], fields[3], fields[4])

def RespondBet(bet: Bet, client_sock: socket):
    response = bet.agency.to_bytes(1, byteorder='big')
    n = 0
    while n < len(response):
        n += client_sock.send(response[n:])

def ReadFromSocket(client_sock: socket, size: int):
    bytes_read = []
    read = 0
    while read < size:
        chunk = client_sock.recv(min(MAX_BUFFER_SIZE, size - read))
        bytes_read += list(chunk)
        read += len(chunk)
    return bytes_read