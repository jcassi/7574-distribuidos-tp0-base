package common

import (
	"bufio"
	"fmt"
	"io"
	"net"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	log "github.com/sirupsen/logrus"
)

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopLapse     time.Duration
	LoopPeriod    time.Duration
}

// Client Entity that encapsulates how
type Client struct {
	config ClientConfig
	conn   net.Conn
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config: config,
	}
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Fatalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}
	c.conn = conn
	return nil
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {
	// autoincremental msgID to identify every message sent
	msgID := 1
	sigchnl := make(chan os.Signal, 1)
	signal.Notify(sigchnl, syscall.SIGINT, syscall.SIGTERM)

loop:
	// Send messages if the loopLapse threshold has not been surpassed
	for timeout := time.After(c.config.LoopLapse); ; {
		select {
		case <-timeout:
			log.Infof("action: timeout_detected | result: success | client_id: %v",
				c.config.ID,
			)
			break loop
		default:
		}

		// Create the connection the server in every loop iteration. Send an
		c.createClientSocket()

		// TODO: Modify the send to avoid short-write
		fmt.Fprintf(
			c.conn,
			"[CLIENT %v] Message N°%v\n",
			c.config.ID,
			msgID,
		)
		msg, err := bufio.NewReader(c.conn).ReadString('\n')
		msgID++
		c.conn.Close()

		if err != nil {
			log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
				c.config.ID,
				err,
			)
			return
		}
		log.Infof("action: receive_message | result: success | client_id: %v | msg: %v",
			c.config.ID,
			msg,
		)

		// Wait a time between sending one message and the next one
		nextIteration := time.After(c.config.LoopPeriod)
		select {
		case <-nextIteration:
		case <-sigchnl:
			log.Infof("action: signal_handling | result: success | client_id: %v", c.config.ID)
			break loop
		}
	}

	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}

// Sends bet to the server and receives ACK
func (c *Client) SendBet(bet Bet) {
	c.createClientSocket()

	err := SendBet(bet, c.conn)
	if err != nil {
		log.Errorf("action: apuesta_enviada | result: fail | dni: %s | numero: %s", bet.document, bet.number)
		c.conn.Close()
		return
	}

	log.Infof("action: apuesta_enviada | result: in_progress | dni: %s | numero: %s", bet.document, bet.number)

	err = ReceiveAck(c.conn)
	if err != nil {
		log.Errorf("action: apuesta_enviada | result: fail | dni: %s | numero: %s", bet.document, bet.number)
		c.conn.Close()
		return
	}

	c.conn.Close()

	log.Infof("action: apuesta_enviada | result: success | dni: %s | numero: %s", bet.document, bet.number)
}

// Reads the bets from the filename received as parameters, sends them in batches and receives its ACKs
func (c *Client) SendBets(filename string, betsByBatch uint) {
	file, err := os.Open(filename)
	if err != nil {
		log.Fatal(err)
	}
	reader := bufio.NewReader(file)
	isEOF := false
	for !isEOF {
		var bets []Bet
		log.Info("action: leer_batch_archivo | result: in_progress")
		isEOF, bets, err = c.ReadBatchFromFile(reader, betsByBatch)
		if err != nil {
			log.Errorf("action: leer_batch_archivo | result: fail")
		}
		log.Info("action: leer_batch_archivo | result: success")

		c.createClientSocket()
		log.Info("action: enviar_batch | result: in_progress")
		err := SendBets(bets, c.conn, c.config.ID)
		if err != nil {
			log.Error("action: enviar_batch | result: fail")
			c.conn.Close()
		}
		log.Info("action: enviar_batch | result: success")
		bets = nil

		log.Info("action: recibir_ack_batch | result: in_progress")
		err = ReceiveAckBets(c.conn, c.config.ID)
		if err != nil {
			log.Error("action: recibir_ack_batch | result: fail")
			c.conn.Close()
			return
		}
		log.Info("action: recibir_ack_batch | result: success")

		c.conn.Close()
	}
}

// Read the amount of lines specified in the environment, creates a bet for each line and returns them.
// Returns whether it has reached EOF, the bets and error
func (c *Client) ReadBatchFromFile(reader *bufio.Reader, betsByBatch uint) (bool, []Bet, error) {
	isEOF := false
	var bets []Bet

	var i uint
	for i = 0; i < betsByBatch; i++ {
		line, err := reader.ReadString('\n')
		if err == io.EOF {
			isEOF = true
			break
		}
		if err != nil {
			return false, nil, err
		}
		fields := strings.Split(strings.TrimSpace(line), ",")
		bets = append(bets, *NewBet(c.config.ID, fields[1], fields[0], fields[2], fields[3], fields[4]))
	}
	return isEOF, bets, nil
}
