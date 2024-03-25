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

#TODO refactor this
def receive_packet(client_sock):
    bytes_read = []
    read = 0
    payload_size = 0
    packet_type = 0
    know_size = False
    while read < payload_size + PACKET_TYPE_LEN + CLIENT_ID_LEN:
        client_sock.settimeout(0.5)
        try:
            chunk = client_sock.recv(1024)
        except socket.timeout:
            logging.error(f'action: receive_batch | result: fail | error: timed out | ip: {client_sock.getpeername()[0]}')
            return None
        bytes_read += list(chunk)
        read += len(chunk)

        if not know_size:
            if read >= PACKET_TYPE_LEN + CLIENT_ID_LEN:
                if bytes_read[0] == 0:
                    packet_type = 0
                elif bytes_read[0] == 1:
                    packet_type = 1
                elif bytes_read[0] == 2:
                    packet_type = 2
                else:
                    return None
            else:
                continue
        
        if packet_type == 0:
            if not know_size:
                if read >= PACKET_TYPE_LEN + CLIENT_ID_LEN + PAYLOAD_LEN:
                    payload_size = bytes_read[2] << 8 | bytes_read[3]
                    know_size = True
                else:
                    continue
            if know_size:
                if read <= PACKET_TYPE_LEN + CLIENT_ID_LEN + PAYLOAD_LEN + payload_size:
                    continue
        elif packet_type == 1 or packet_type == 2:
            payload_size = 0
            know_size = True

    if packet_type == PACKET_TYPE_BATCH:
        return (PACKET_TYPE_BATCH, __deserialize_batch(bytes_read))
    elif packet_type == PACKET_TYPE_NOTIFY:
        return (PACKET_TYPE_NOTIFY, __deserialize_notify(bytes_read))
    elif packet_type == PACKET_TYPE_QUERY:
        return (PACKET_TYPE_QUERY, __deserialize_query(bytes_read))
    else:
        return None
        

def __deserialize_batch(bytes_read):
    """
    TODO
    """
    payload_size = len(bytes_read) - (PACKET_TYPE_LEN + CLIENT_ID_LEN + PAYLOAD_LEN)
    agency = str(int(bytes_read[1]))
    bets = []
    position = PACKET_TYPE_LEN + CLIENT_ID_LEN + PAYLOAD_LEN
    while position < payload_size + PACKET_TYPE_LEN + CLIENT_ID_LEN + PAYLOAD_LEN - 1:
        bet = __deserialize_bet(agency, bytes_read[position:])           
        if bet is None:
            logging.error(f'action: deserialize_bet | result: fail | agency: {agency}') # TODO addr
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