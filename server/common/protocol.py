import logging
from common.utils import Bet

def ReceiveBet(client_sock):
    bytes_read = []
    read = 0
    size = 2
    while read < size:
        chunk = client_sock.recv(1024)
        bytes_read += list(chunk)
        data_length = len(chunk)
        if read == 0 and data_length >= 2:
            size = bytes_read[0] << 8 | bytes_read[1]
            read += data_length

    if (size < 4): #Can't be less than 2 bytes of length, 1 of client_id and at least 1 of payload
        logging.info(f'action: apuesta_almacenada | result: fail | ip: {addr[0]} | msg: {msg}')
        return None
    client_id = int(bytes_read[2])
    msg = bytes(bytes_read[3:]).decode("utf-8")
    addr = client_sock.getpeername()
    logging.info(f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg}')
    fields = msg.split(',')

    return Bet(client_id, fields[0], fields[1], fields[2], fields[3], fields[4])

def RespondBet(bet, client_sock):
    response_payload = "{}".format(bet.number).encode('utf-8')
    response_len = len(response_payload).to_bytes(1, byteorder='big')
    response = response_len + response_payload
    n = 0
    while n < len(response):
        n += client_sock.send(response[n:])