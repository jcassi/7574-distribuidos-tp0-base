import socket
import logging
import signal
from common.utils import Bet, Notify, Query, has_won, load_bets, store_bets
from common.protocol import PACKET_TYPE_BATCH, PACKET_TYPE_NOTIFY, PACKET_TYPE_QUERY, receive_packet, respond_bets, respond_notify, respond_query
from multiprocessing import Array, Process, Lock, Value


class Server:
    def __init__(self, port, listen_backlog, clients_count: int):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._stop = Value('i', 0)
        self._finished_clients = Array('i', [0] * clients_count )
        self._client_handlers = []
        self._file_lock = Lock()

        signal.signal(signal.SIGINT, self.__graceful_shutdown)
        signal.signal(signal.SIGTERM, self.__graceful_shutdown)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        stop = False
        while not stop:
            client_sock = self.__accept_new_connection()
            if client_sock is None:
                break
            client_handler = Process(target=self.__handle_client_connection, args=(client_sock,self._file_lock, self._finished_clients))
            self._client_handlers.append(client_handler)
            client_handler.start()
            with self._stop.get_lock():
                stop = self._stop == 1

        for handler in self._client_handlers:
            handler.join()

    def __handle_client_connection(self, client_sock, lock_file, finished_clients):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            addr = client_sock.getpeername()[0]
            close_connection = False
            while not close_connection:
                packet = receive_packet(client_sock)
                if packet is not None:
                    (packet_type, msg) = packet
                    if packet_type == PACKET_TYPE_BATCH:
                        self.__process_bets(msg, client_sock, lock_file)
                    elif packet_type == PACKET_TYPE_NOTIFY:
                        self.__process_notify(msg, client_sock, finished_clients)
                        close_connection = True
                    elif packet_type == PACKET_TYPE_QUERY:
                        self.__process_query(msg, client_sock, lock_file, finished_clients)
                        close_connection = True
                else:
                    close_connection = True
                with self._stop.get_lock():
                    close_connection = self._stop == 1
            
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
        with self._stop.get_lock():
            self._stop = 1
        logging.info("action: signal_handling | result: success")

    def __process_bets(self, bets: list[Bet], client_sock: socket, lock):
        lock.acquire()
        store_bets(bets)
        lock.release()
        logging.info(f'action: apuesta_almacenada | result: success')
        respond_bets(client_sock)

    def __process_notify(self, notify: Notify, client_sock: socket, finished_clients):
        with finished_clients.get_lock():
            finished_clients[notify.agency-1] = 1
        respond_notify(client_sock)

        
    def __process_query(self, query: Query, client_sock, lock_file, finished_clients):
        logging.info("action: pedido_sorteo | result: in_progress")
        winners = []
        can_lottery = True
        with finished_clients.get_lock():
            for i in range(len(finished_clients)):
                if finished_clients[i] == 0:
                    can_lottery = False
        if can_lottery:
            logging.info("action: sorteo | result: success")
            lock_file.acquire()
            bets = load_bets()
            lock_file.release()
            for bet in bets:
                if bet.agency == query.agency and has_won(bet):
                    winners.append(bet.document)
            respond_query(True, winners, client_sock)
        else:
            logging.info("action: sorteo | result: rejected")
            respond_query(False, winners, client_sock)
