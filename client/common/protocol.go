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
	return nil
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
	buffer := make([]byte, 1)
	read := 0
	size := 1
	for read < size {
		n, err := conn.Read(buffer)
		if err != nil {
			return err
		}
		if n > 0 {
			//log.Infof("bets ack %v", buffer[0])
			if buffer[0] == PACKET_TYPE_BATCH_ACK {
				return nil
			} else {
				return fmt.Errorf("expected packet type %v, received %v", PACKET_TYPE_BATCH_ACK, buffer[0])
			}
		}
		read += n
	}

	return nil
}

// Function to send all the bytes received as the first parameter over the connection received
// as the second parameter.
func SendToSocket(bytes []byte, conn net.Conn) error {
	//log.Infof("%v", bytes)
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

	return SendToSocket(bytes, conn)
}

func QueryWinners(agency string, conn net.Conn) error {
	id, _ := strconv.Atoi(agency)
	bytes := []byte{PACKET_TYPE_QUERY, uint8(id)}

	return SendToSocket(bytes, conn)
}

func ReceiveAckNotify(conn net.Conn, clientId string) error {
	buffer := make([]byte, 1)
	read := 0
	size := 1
	for read < size {
		n, err := conn.Read(buffer)
		if err != nil {
			return err
		}
		if n > 0 {
			//log.Infof("notify ack %v", buffer[0])
			if buffer[0] == PACKET_TYPE_NOTIFY_ACK {
				return nil
			} else {
				log.Error("mal")
			}
		}
		read += n
	}

	return nil
}

func ReceiveAckQuery(conn net.Conn, clientId string) ([]string, error) {
	buffer := make([]byte, 1024)
	read := 0
	size := 4
	knowSize := false
	var winners []string

	for read < size { //TODO timeout?
		n, err := conn.Read(buffer)
		if err != nil {
			return nil, err
		}
		read += n
		if read < 4 {
			continue
		}

		if buffer[0] != PACKET_TYPE_QUERY_RESPONSE {
			return nil, fmt.Errorf("expected packet type %v, received %v", PACKET_TYPE_QUERY_RESPONSE, buffer[0])
		}
		if !knowSize {
			size = int(uint16(buffer[2])<<8 | uint16(buffer[3]))
			//log.Infof("size %v", size)
		}
	}

	myString := string(buffer[4 : 4+size])
	winners = strings.Split(myString, ",")
	return winners, nil
}
