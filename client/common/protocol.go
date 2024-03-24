package common

import (
	"fmt"
	"net"
	"strconv"
)

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
	id, _ := strconv.Atoi(bet.agency) //TODO ver error
	aux := append(uint16ToBytes(len), uint8(id))
	return append(aux, betBytes...)
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
