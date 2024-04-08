import logging
import socket
from common.utils import Bet, Notify, Query
from enum import Enum
 
class PacketType(Enum):
    BATCH = 1
    DRAW = 2

PACKET_TYPE_LEN = 1
PAYLOAD_LEN = 2
CLIENT_ID_LEN = 1

PACKET_TYPE_BATCH = 0
PACKET_TYPE_NOTIFY = 1
PACKET_TYPE_QUERY = 2
PACKET_TYPE_BATCH_ACK = 3
PACKET_TYPE_NOTIFY_ACK = 4
PACKET_TYPE_QUERY_RESPONSE = 5

PACKET_QUERY_RESPONSE_SUCCESS = 0
PACKET_QUERY_RESPONSE_FAILURE = 1

MAX_BUFFER_SIZE = 1024

def receive_packet(client_sock: socket):
    bytes_read = __read_from_socket(client_sock, PACKET_TYPE_LEN + CLIENT_ID_LEN + PAYLOAD_LEN)
    packet_type = bytes_read[0]
    agency = int(bytes_read[1])
    size = bytes_read[2] << 8 | bytes_read[3]

    if packet_type == PACKET_TYPE_BATCH:
        bytes_read = __read_from_socket(client_sock, size)
        return (PACKET_TYPE_BATCH, __deserialize_batch(bytes_read, agency))
    elif packet_type == PACKET_TYPE_NOTIFY:
        return (PACKET_TYPE_NOTIFY, __deserialize_notify(bytes_read))
    elif packet_type == PACKET_TYPE_QUERY:
        return (PACKET_TYPE_QUERY, __deserialize_query(bytes_read))
    else:
        return None
        

def __deserialize_batch(bytes_read, agency: int):
    bets = []
    position = 0
    while position < len(bytes_read) - 1:
        bet = __deserialize_bet(agency, bytes_read[position:])           
        if bet is None:
            logging.error(f'action: deserialize_bet | result: fail | agency: {agency}')
            return None
        else:
            (n, bet) = bet
            bets.append(bet)
            position += n
    return bets

def __deserialize_notify(bytes_read):
    return Notify(int(bytes_read[1]))

def __deserialize_query(bytes_read):
    return Query(int(bytes_read[1]))

def __deserialize_bet(agency: str, betsBytes: bytes):
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


def respond_bets(client_sock: socket):
    """
    Sends ACK to the client
    """
    logging.info(f'action: sending_batch_ack | result: in_progress | ip: {client_sock.getpeername()[0]}')
    response = PACKET_TYPE_BATCH_ACK.to_bytes(1, byteorder='big')
    try:
        __send_bytes(response, client_sock)
    except OSError as e:
        logging.error(f'action: sending_batch_ack | result: fail | ip: {client_sock.getpeername()[0]} | error: {e}')
        raise e
    logging.info(f'action: sending_batch_ack | result: success | ip: {client_sock.getpeername()[0]}')

def respond_notify(client_sock: socket):
    """
    Sends ACK to the client
    """
    logging.info(f'action: sending_notify_ack | result: in_progress | ip: {client_sock.getpeername()[0]}')
    response = PACKET_TYPE_NOTIFY_ACK.to_bytes(1, byteorder='big')
    try:
        __send_bytes(response, client_sock)
    except OSError as e:
        logging.error(f'action: sending_notify_ack | result: fail | ip: {client_sock.getpeername()[0]} | error: {e}')
        raise e
    logging.info(f'action: sending_notify_ack | result: success | ip: {client_sock.getpeername()[0]}')

def respond_query(can_respond: bool, winners: list[str], client_sock: socket):
    response = []
    if can_respond:
        response.append(PACKET_TYPE_QUERY_RESPONSE.to_bytes(1, 'big'))
        response.append(PACKET_QUERY_RESPONSE_SUCCESS.to_bytes(1, 'big'))

        winners_bytes = ",".join(winners).encode('utf-8')
        response.append(len(winners_bytes).to_bytes(2, 'big'))
        response.append(winners_bytes)
        response =  b''.join(response)
    else:
        response.append(PACKET_TYPE_QUERY_RESPONSE.to_bytes(1, 'big'))
        response.append(PACKET_QUERY_RESPONSE_FAILURE.to_bytes(1, 'big'))
        length = 0
        response.append(length.to_bytes(2, 'big'))
        response =  b''.join(response)
    try:
        __send_bytes(response, client_sock)
    except OSError as e:
        raise e
            
def __send_bytes(bytes_list: bytes, client_sock: socket):
    n = 0
    while n < len(bytes_list):
        n += client_sock.send(bytes_list[n:])

def __read_from_socket(client_sock: socket, size: int):
    bytes_read = []
    read = 0
    while read < size:
        chunk = client_sock.recv(min(MAX_BUFFER_SIZE, size - read))
        bytes_read += list(chunk)
        read += len(chunk)
    return bytes_read