class AbbreviationTable:
    def __init__(self, start_location, memory):
        self.startLocation = start_location
        self.memory = memory

    def toString(self, n):
        location = self.startLocation + n * 2
        address = int.from_bytes(self.memory[location:location + 2], 'big') * 2
        return toZString(address, self.memory)


alphabet_A0 = "abcdefghijklmnopqrstuvwxyz"
alphabet_A1 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
alphabet_A2 = " ^0123456789.,!?_#'\"/\\-:()"

current_alphabet = alphabet_A0


def fromZChar(value):
    global current_alphabet
    if value == 0:
        current_alphabet = alphabet_A0
        return " "
    elif value == 4:
        current_alphabet = alphabet_A1
        return ""
    elif value == 5:
        current_alphabet = alphabet_A2
        return ""
    else:
        c = current_alphabet[value - 6]
        current_alphabet = alphabet_A0
        return c


def toZString(address, memory):
    global current_alphabet
    current_alphabet= alphabet_A0
    result = ""
    done = False
    while not done:
        word = int.from_bytes(memory[address:address + 2], 'big')
        address += 2
        top = word & 0x8000
        first = word >> 10 & 0x1F
        second = word >> 5 & 0x1F
        third = word & 0x1F
        result = result + fromZChar(first) + fromZChar(second) + fromZChar(third)
        if top:
            done = True
    return result
