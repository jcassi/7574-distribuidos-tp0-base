package common

import (
	"fmt"
	"net"
	"strconv"
	"strings"

	log "github.com/sirupsen/logrus"
)

const MAX_PACKET_SIZE = 8192
const PACKET_TYPE_BATCH = 0
const PACKET_TYPE_NOTIFY = 1
const PACKET_TYPE_QUERY = 2
const PACKET_TYPE_BATCH_ACK = 3
const PACKET_TYPE_NOTIFY_ACK = 4
const PACKET_TYPE_QUERY_RESPONSE = 5

const PACKET_QUERY_RESPONSE_SUCCESS = 0
const PACKET_QUERY_RESPONSE_FAILURE = 1

const PACKET_QUERY_RESPONSE_MIN_LEN = 4

const MAX_BUFFER_SIZE = 1024

// Receives a slice of bets, serializes them and sends them to the server over the connection received as parameter
func SendBets(bets []Bet, conn net.Conn, clientId string, betsByBatch uint) error {
	i := 0
	for i < len(bets) {
		n, batchBytes := BatchToBytes(clientId, bets[i:], betsByBatch)
		i += n
		err := SendToSocket(batchBytes, conn)
		if err != nil {
			return err
		}
	}
	return ReceiveAckBets(conn, clientId)
}

// Converts a slice of bets to the bytes according to the protocol
func BatchToBytes(agency string, bets []Bet, betsByBatch uint) (int, []byte) {
	var batchBytes []byte
	n := 0
	i := 0
	for ; i < len(bets) && n < int(betsByBatch); i++ {
		bet := bets[i]
		betBytes := SerializeBet(bet)
		if len(batchBytes)+len(betBytes) < MAX_PACKET_SIZE {
			batchBytes = append(batchBytes, betBytes...)
			n++
		}
	}

	var len uint16 = uint16(len(batchBytes))
	id, _ := strconv.Atoi(agency)
	aux := []byte{PACKET_TYPE_BATCH, uint8(id)}
	aux = append(aux, uint16ToBytes(len)...)
	batchBytes = append(aux, batchBytes...)
	return n, batchBytes
}

// Receives the ACK message sent by the server through the connection received as parameter
// Checks that the ACK is correct by checking that the client_id is the same as this client's id
func ReceiveAckBets(conn net.Conn, clientId string) error {
	log.Info("action: recibir_ack_batch | result: in_progress")
	bytes, err := ReadFromSocket(conn, 1)
	if err != nil {
		return err
	}
	if bytes[0] == PACKET_TYPE_BATCH_ACK {
		log.Info("action: recibir_ack_batch | result: success")
		return nil
	} else {
		err = fmt.Errorf("expected packet type %v, received %v", PACKET_TYPE_BATCH_ACK, bytes[0])
		log.Errorf("action: recibir_ack_batch | result: fail | error %s", err)
		return err
	}
}

// Function to send all the bytes received as the first parameter over the connection received
// as the second parameter.
func SendToSocket(bytes []byte, conn net.Conn) error {
	sent := 0
	for sent < len(bytes) {
		n, err := fmt.Fprintf(conn, "%s", bytes[sent:])
		if err != nil {
			return err
		}
		sent += n
	}
	return nil
}

// Sends the bet in a serialized format over the connection received as paramater
func SendBet(bet Bet, conn net.Conn) error {
	betBytes := SerializeBet(bet)
	sent := 0
	for sent < len(betBytes) {
		n, err := fmt.Fprintf(conn, "%s", betBytes[sent:])
		if err != nil {
			return err
		}
		sent += n
	}

	return nil
}

// Receives confirmation that the server received the bet
func ReceiveAck(conn net.Conn) error {
	buffer := make([]byte, 257)
	read := 0
	size := 1
	readResponseSize := true
	for read < size {
		n, err := conn.Read(buffer)
		if err != nil {
			return err
		}
		if n > 0 && readResponseSize {
			size = int(buffer[0])
			readResponseSize = false
		}
		read += n
	}

	return nil
}

// Serializes a bet. Check docks to see the serialization format
func SerializeBet(bet Bet) []byte {
	betBytes := BetToBytes(bet)
	var len uint16 = uint16(len(betBytes))
	return append(uint16ToBytes(len), betBytes...)
}

func uint16ToBytes(n uint16) []byte {
	var h, l uint8 = uint8(n >> 8), uint8(n & 0xff)
	return []byte{h, l}
}

// Returns a slice of bytes with the bet fields separated by commas
func BetToBytes(bet Bet) []byte {
	str := fmt.Sprintf("%s,%s,%s,%s,%s", bet.firstName, bet.lastName, bet.document, bet.birthDate, bet.number)
	return []byte(str)
}

func NotifyServer(agency string, conn net.Conn) error {
	id, _ := strconv.Atoi(agency)
	bytes := []byte{PACKET_TYPE_NOTIFY, uint8(id)}
	bytes = append(bytes, uint16ToBytes(0)...) //Add length 0

	err := SendToSocket(bytes, conn)
	if err != nil {
		return err
	}
	return ReceiveAckNotify(conn, agency)
}

func QueryWinners(agency string, conn net.Conn) ([]string, error) {
	id, _ := strconv.Atoi(agency)
	bytes := []byte{PACKET_TYPE_QUERY, uint8(id)}
	bytes = append(bytes, uint16ToBytes(0)...) //Add length 0

	err := SendToSocket(bytes, conn)
	if err != nil {
		return nil, err
	}
	return ReceiveQueryResponse(conn, agency)
}

func ReceiveAckNotify(conn net.Conn, clientId string) error {
	log.Info("action: recibir_ack_batch | result: in_progress")
	bytes, err := ReadFromSocket(conn, 1)
	if err != nil {
		return err
	}
	if bytes[0] == PACKET_TYPE_NOTIFY_ACK {
		log.Info("action: recibir_ack_batch | result: success")
		return nil
	} else {
		log.Error("action: recibir_ack_batch | result: fail")
		return fmt.Errorf("expected packet type %v, received %v", PACKET_TYPE_NOTIFY_ACK, bytes[0])
	}
}

func ReceiveQueryResponse(conn net.Conn, clientId string) ([]string, error) {
	log.Info("action: recibir_ganadores | result: in_progress")
	bytes, err := ReadFromSocket(conn, PACKET_QUERY_RESPONSE_MIN_LEN)
	if err != nil {
		return nil, err
	}
	if bytes[0] == PACKET_TYPE_QUERY_RESPONSE {
		if bytes[1] == PACKET_QUERY_RESPONSE_SUCCESS {
			size := int(uint16(bytes[2])<<8 | uint16(bytes[3]))
			bytes, err = ReadFromSocket(conn, size)
			if err != nil {
				return nil, err
			}
			winnersStr := string(bytes[:size])
			winners := strings.Split(winnersStr, ",")
			log.Info("action: recibir_ganadores | result: success")
			return winners, nil
		} else {
			return nil, &LotteryRejection{}
		}

	} else {
		err = fmt.Errorf("expected packet type %v, received %v", PACKET_TYPE_QUERY_RESPONSE, bytes[0])
		log.Errorf("action: recibir_ganadores | result: fail | error %s", err)
		return nil, err
	}
}

func ReceivePacket(conn net.Conn) error {

	return nil
}

type LotteryRejection struct{}

func (m *LotteryRejection) Error() string {
	return "Not all agencies have stopped sending bets"
}

func ReadFromSocket(conn net.Conn, size int) ([]byte, error) {
	var bytes []byte
	buffer := make([]byte, MAX_BUFFER_SIZE)
	read := 0

	for read < size {
		n, err := conn.Read(buffer[:min(MAX_BUFFER_SIZE, size-read)])
		if err != nil {
			return nil, err
		}
		read += n
		bytes = append(bytes, buffer...)
	}
	return bytes, nil
}

func min(x int, y int) int {
	if x < y {
		return x
	} else {
		return y
	}
}
