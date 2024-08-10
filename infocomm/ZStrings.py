alphabet_A0 = "abcdefghijklmnopqrstuvwxyz"
alphabet_A1 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
alphabet_A2 = " \n0123456789.,!?_#'\"/\\-:()"

current_alphabet = alphabet_A0
next_is_abbreviation = False
abbreviation_offset = None


def singleZChar(value):
    if value < 6:
        return ""
    elif value < 6+32:
        return alphabet_A0[value-6]
    else:
        return chr(value)


def fromZChar(value, abbreviation_table):
    global current_alphabet
    global next_is_abbreviation
    global abbreviation_offset

    if next_is_abbreviation:
        next_is_abbreviation = False
        abbrv = abbreviation_table.toString(value + abbreviation_offset)
        # Reset Alphabet after abbreviation
        current_alphabet = alphabet_A0
        return abbrv

    if value == 0:
        current_alphabet = alphabet_A0
        return " "
    elif value == 1:
        next_is_abbreviation = True
        abbreviation_offset = 32 * (value - 1)
        return ""
    elif value == 2:
        next_is_abbreviation = True
        abbreviation_offset = 32 * (value - 1)
        return ""
    elif value == 3:
        next_is_abbreviation = True
        abbreviation_offset = 32 * (value - 1)
        return ""
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


def toZString(address, memory, abbreviation_table, count=None):
    global current_alphabet
    current_alphabet = alphabet_A0
    result = ""
    done = False
    while not done:
        word = int.from_bytes(memory[address:address + 2], 'big')
        address += 2
        top = word & 0x8000
        first = word >> 10 & 0x1F
        second = word >> 5 & 0x1F
        third = word & 0x1F
        result = (result + fromZChar(first, abbreviation_table)
                  + fromZChar(second, abbreviation_table)
                  + fromZChar(third, abbreviation_table))
        if top:
            done = True
        if count is not None:
            count -= 1
            if count == 0:
                done = True
    return result
