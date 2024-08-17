alphabet_A0 = "abcdefghijklmnopqrstuvwxyz"
alphabet_A1 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
alphabet_A2 = " \n0123456789.,!?_#'\"/\\-:()"

class ZStringContext:
    def __init__(self):
        self.current_alphabet = alphabet_A0
        self.building_ZSCII = False
        self.partial_ZSCII = None
        self.next_is_abbreviation = False
        self.abbreviation_offset = None


global_zstring_context = ZStringContext()

def singleZSCIIChar(value):
    # TODO... consider ZSCII special cases... e.g. <31 and >126
    return chr(value)


def fromZChar(value, abbreviation_table, context):

    if context.next_is_abbreviation:
        context.next_is_abbreviation = False
        abbrv = abbreviation_table.toString(value + context.abbreviation_offset)
        return abbrv

    if context.building_ZSCII:
        # First pass... None becomes first value
        if context.partial_ZSCII is None:
            context.partial_ZSCII = value
            return ""
        else:
            # Second pass... Combine second value
            zscii = context.partial_ZSCII << 5 | value
            result = singleZSCIIChar(zscii)
            context.building_ZSCII = False
            return result

    if value == 0:
        context.current_alphabet = alphabet_A0
        return " "
    elif value == 1:
        context.next_is_abbreviation = True
        context.abbreviation_offset = 32 * (value - 1)
        return ""
    elif value == 2:
        context.next_is_abbreviation = True
        context.abbreviation_offset = 32 * (value - 1)
        return ""
    elif value == 3:
        context.next_is_abbreviation = True
        context.abbreviation_offset = 32 * (value - 1)
        return ""
    elif value == 4:
        context.current_alphabet = alphabet_A1
        return ""
    elif value == 5:
        context.current_alphabet = alphabet_A2
        return ""
    elif value == 6 and context.current_alphabet == alphabet_A2:
        context.building_ZSCII = True
        context.partial_ZSCII = None
        return ""
    else:
        zscii = context.current_alphabet[value - 6]
        context.current_alphabet = alphabet_A0
        return zscii


def toZString(address, memory, abbreviation_table, count=None, context=None):

    if context is None:
        context = ZStringContext()

    result = ""
    done = False
    while not done:
        word = int.from_bytes(memory[address:address + 2], 'big')
        address += 2
        top = word & 0x8000
        first = word >> 10 & 0x1F
        second = word >> 5 & 0x1F
        third = word & 0x1F
        result = (result + fromZChar(first, abbreviation_table, context)
                  + fromZChar(second, abbreviation_table, context)
                  + fromZChar(third, abbreviation_table, context))
        if top:
            done = True
        if count is not None:
            count -= 1
            if count == 0:
                done = True
    return result
