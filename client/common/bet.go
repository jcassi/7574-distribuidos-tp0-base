package common

type Bet struct {
	agency    string
	firstName string
	lastName  string
	document  string
	birthDate string
	number    string
}

// Creates a bet
func NewBet(agency string, firstName string, lastName string, document string, birthDate string, number string) *Bet {
	bet := &Bet{
		agency:    agency,
		firstName: firstName,
		lastName:  lastName,
		document:  document,
		birthDate: birthDate,
		number:    number,
	}
	return bet
}
