alphabet_A0 = r"""^^^^^^abcdefghijklmnopqrstuvwxyz"""
alphabet_A1 = r"""^^^^^^ABCDEFGHIJKLMNOPQRSTUVWXYZ"""
alphabet_A2 = r"""^^^^^^^^0123456789.,!?_#’"/\-:()"""
alphabet_a2 = r"""^^^^^^^0123456789.,!?_#’"/\<-:()"""  # V1?


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
            # Reset from escaped A2 back to default
            context.current_alphabet = alphabet_A0
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
    elif value == 7 and context.current_alphabet == alphabet_A2:
        zscii = "\n"
        context.current_alphabet = alphabet_A0
        return zscii
    else:
        zscii = context.current_alphabet[value]
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


def convertToEncodedWords(s):
    index = 0
    words_to_encode = 2
    five_bits_to_encode = words_to_encode * 3
    five_bits = []

    while len(five_bits) < five_bits_to_encode:
        if index < len(s):
            c = s[index]
            index += 1

            # Encode C as five bits
            if c != "^" and c in alphabet_A0:
                five_bits.append(alphabet_A0.index(c))
            elif c != "^" and c in alphabet_A1:
                append_if_space(five_bits, [4, alphabet_A1.index(c)], five_bits_to_encode)
            elif c != "^" and c in alphabet_A2:
                append_if_space(five_bits, [5, alphabet_A2.index(c)], five_bits_to_encode)
            else:
                value = ord(c)
                append_if_space(five_bits, [5, 6, value >> 5, value & 0b11111], five_bits_to_encode)
        else:
            five_bits.append(5)

    # Now convert to words with last one having top bit set
    words = []
    ifive_bits = iter(five_bits)
    for a, b, c in zip(ifive_bits, ifive_bits, ifive_bits):
        words.append(a << 10 | b << 5 | c)

    words[-1] |= 0x8000

    return words


def append_if_space(five_bits, extra_bits, max_bits):
    if len(five_bits) + len(extra_bits) <= max_bits:
        return five_bits.extend(extra_bits)
    else:
        return five_bits.extend([5] * (max_bits - len(five_bits)))
