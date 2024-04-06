import logging
import socket
from common.utils import Bet

PAYLOAD_LEN = 2
CLIENT_ID_LEN = 1
MAX_BUFFER_SIZE = 1024

def receive_bets(client_sock):
    """
    Read batch bets from socket, deserialize them and return the bets
    """
    bytes_read = __read_from_socket(client_sock, PAYLOAD_LEN + CLIENT_ID_LEN)
    agency = int(bytes_read[0])
    size = bytes_read[1] << 8 | bytes_read[2]
    addr = client_sock.getpeername()

    bytes_read = __read_from_socket(client_sock, size)
    bets = []
    position = 0
    while position < size - 1:
        bet = __deserialize_bet(agency, bytes_read[position:])
        if bet is None:
            logging.error(f'action: deserialize_bet | result: fail | ip: {addr[0]} | agency: {agency}')
            return None
        else:
            (n, bet) = bet
            bets.append(bet)
            position += n
    return bets

def __deserialize_bet(agency, betsBytes):
    """
    Read bytes belonging to one bet from a list of bytes and deserialize them into a bet.
    Return the next position to read from the list and the bet deserialized
    """
    if len(betsBytes) < PAYLOAD_LEN:
        return None
    size = betsBytes[0] << 8 | betsBytes[1]
    if len(betsBytes) < PAYLOAD_LEN + size:
        return None
    msg = bytes(betsBytes[PAYLOAD_LEN:PAYLOAD_LEN + size]).decode("utf-8")
    fields = msg.split(',')
    if len(fields) != 5:
        return None

    return (size + PAYLOAD_LEN, Bet(agency, fields[1], fields[0], fields[2], fields[3], fields[4]))


def respond_bets(client_sock, agency):
    """
    Sends ACK to the client
    """
    logging.info(f'action: sending_batch_ack | result: in_progress | ip: {client_sock.getpeername()[0]}')
    response = int(agency).to_bytes(1, byteorder='big')
    n = 0
    try:
        while n < len(response):
            n += client_sock.send(response[n:])
    except OSError as e:
        logging.error(f'action: sending_batch_ack | result: fail | ip: {client_sock.getpeername()[0]} | error: {e}')
        raise e
    logging.info(f'action: sending_batch_ack | result: success | ip: {client_sock.getpeername()[0]}')


def __read_from_socket(client_sock: socket, size: int):
    bytes_read = []
    read = 0
    while read < size:
        chunk = client_sock.recv(min(MAX_BUFFER_SIZE, size - read))
        bytes_read += list(chunk)
        read += len(chunk)
    return bytes_read