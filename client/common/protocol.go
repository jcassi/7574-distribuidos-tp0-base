package common

import (
	"fmt"
	"net"
	"strconv"
)

const MAX_PACKET_SIZE = 8192

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
	aux := []byte{uint8(id)}
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
			id := fmt.Sprintf("%v", buffer[0])
			if id == clientId {
				return nil
			}
		}
		read += n
	}

	return nil
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
