package common

type Bet struct {
	firstName string
	lastName  string
	document  string
	birthDate string
	number    string
}

// Creates a bet
func NewBet(firstName string, lastName string, document string, birthDate string, number string) *Bet {
	bet := &Bet{
		firstName: firstName,
		lastName:  lastName,
		document:  document,
		birthDate: birthDate,
		number:    number,
	}
	return bet
}
