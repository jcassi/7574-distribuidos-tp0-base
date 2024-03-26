import socket
import logging
import signal
from common.utils import Bet, Notify, Query, has_won, load_bets, store_bets
from common.protocol import PACKET_TYPE_BATCH, PACKET_TYPE_NOTIFY, PACKET_TYPE_QUERY, receive_packet, respond_bets, respond_notify, respond_query


class Server:
    def __init__(self, port, listen_backlog, clients_count: int):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._stop = False
        self._finished_clients = []
        self._clients_count = clients_count
        signal.signal(signal.SIGINT, self.__graceful_shutdown)
        signal.signal(signal.SIGTERM, self.__graceful_shutdown)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        while not self._stop:
            client_sock = self.__accept_new_connection()
            if client_sock is None:
                break
            self.__handle_client_connection(client_sock)

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            addr = client_sock.getpeername()[0]
            packet = receive_packet(client_sock)
            if packet is not None:
                (packet_type, msg) = packet
                if packet_type == PACKET_TYPE_BATCH:
                    self.__process_bets(msg, client_sock)
                elif packet_type == PACKET_TYPE_NOTIFY:
                    self.__process_notify(msg, client_sock)
                elif packet_type == PACKET_TYPE_QUERY:
                    self.__process_query(msg, client_sock)
            
            client_sock.shutdown(socket.SHUT_RDWR)
        except OSError as e:
            logging.error(f"action: receive_message | result: fail | error: {e}")
        finally:
            logging.info(f'action: close_client_socket | result: in_progress | ip {addr}')
            client_sock.close()
            logging.info(f'action: close_client_socket | result: success | ip {addr}')

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info('action: accept_connections | result: in_progress')
        try:
            c, addr = self._server_socket.accept()
        except OSError:
            return None
        logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
        return c

    def __graceful_shutdown(self, signum, frame):
        logging.info("action: signal_handling | result: in_progress")
        self._server_socket.shutdown(socket.SHUT_RDWR)
        self._server_socket.close()
        self._stop = True
        logging.info("action: signal_handling | result: success")

    def __process_bets(self, bets: list[Bet], client_sock):
        store_bets(bets)
        logging.info(f'action: apuesta_almacenada | result: success') #TODO addr
        respond_bets(client_sock)

    def __process_notify(self, notify: Notify, client_sock):
        #logging.info("proceso notify")
        if not notify.agency in self._finished_clients:
            self._finished_clients.append(notify.agency)
        #logging.info("RESPONDO notify")
        respond_notify(client_sock)

        
    def __process_query(self, query: Query, client_sock):
        logging.info("action: pedido_sorteo | result: in_progress")
        winners = []
        if len(self._finished_clients) == self._clients_count:
            logging.info("action: sorteo | result: success")
            bets = load_bets()
            for bet in bets:
                if bet.agency == query.agency and has_won(bet):
                    winners.append(bet.document)
            respond_query(True, winners, client_sock)
        else:
            logging.info("action: sorteo | result: rejected")
            respond_query(False, winners, client_sock)
