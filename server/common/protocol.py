import logging
from common.utils import Bet

PAYLOAD_LEN = 2
CLIENT_ID_LEN = 1

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

    addr = client_sock.getpeername()
    if (size < PAYLOAD_LEN + CLIENT_ID_LEN + 1): #Can't be less than 2 bytes of length, 1 of client_id and at least 1 of payload
        logging.info(f'action: apuesta_almacenada | result: fail | ip: {addr[0]} | msg: {msg}') #TODO ver mensaje de error
        return None
    client_id = int(bytes_read[2])
    msg = bytes(bytes_read[3:]).decode("utf-8")
    
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

def receive_bets(client_sock):
    """
    Read batch bets from socket, deserialize them and return the bets
    """
    bytes_read = __read_batch_bytes(client_sock)
    size = len(bytes_read) - PAYLOAD_LEN - CLIENT_ID_LEN

    agency = str(int(bytes_read[2]))
    addr = client_sock.getpeername()

    bets = []
    position = PAYLOAD_LEN + CLIENT_ID_LEN
    while position < size + PAYLOAD_LEN + CLIENT_ID_LEN - 1:
        (n, bet) = __deserialize_bet(agency, bytes_read[position:]) #TODO chequear que no sea None
        bets.append(bet)
        position += n
    return bets

def __read_batch_bytes(client_sock):
    """
    Read bytes from a batch of bets and return them raw
    """
    bytes_read = []
    read = 0
    size = PAYLOAD_LEN
    logging.info('action: receive_batch | result: in_progress')
    try:
        while read < size + PAYLOAD_LEN + CLIENT_ID_LEN:
            chunk = client_sock.recv(1024)
            bytes_read += list(chunk)
            data_length = len(chunk)
            if read == 0 and data_length >= 2:
                size = bytes_read[0] << 8 | bytes_read[1]
                read += data_length
    except OSError as e:
        logging.info('action: receive_batch | result: fail')
        raise e
    logging.info('action: receive_batch | result: success')
    return bytes_read

def __deserialize_bet(agency, betsBytes):
    """
    Read bytes belonging to one bet from a list of bytes and deserialize them into a bet.
    Return the next position to read from the list and the bet deserialized
    """
    if len(betsBytes) < 4:
        return None
    size = betsBytes[0] << 8 | betsBytes[1]
    msg = bytes(betsBytes[PAYLOAD_LEN:PAYLOAD_LEN + size]).decode("utf-8")
    fields = msg.split(',')
    if len(fields) != 5:
        logging.error(f'len fields {len(fields)}')
        return None

    return (size + PAYLOAD_LEN, Bet(agency, fields[1], fields[0], fields[2], fields[3], fields[4]))


def respond_bets(client_sock, agency):
    """
    Sends ACK to the client
    """
    logging.info('action: sending_batch_ack | result: in_progress')
    response = int(agency).to_bytes(1, byteorder='big')
    n = 0
    try:
        while n < len(response):
            n += client_sock.send(response[n:])
    except OSError as e:
        logging.info('action: sending_batch_ack | result: fail')
        raise e
    logging.info('action: sending_batch_ack | result: success')