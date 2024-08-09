class Utils:
    @staticmethod
    def mread_word(memory, offset):
        return int.from_bytes(memory[offset:offset + 2], 'big', signed=False)

    @staticmethod
    def mwrite_word(memory, offset, value):
        memory[offset] = (value >> 8) & 0xFF
        memory[offset+1] = value & 0xFF

    @staticmethod
    def from_unsigned_word_to_signed_int(i):
        return i if i < 32668 else i - 65536

    @staticmethod
    def from_signed_int_to_bytes(i):
        return i.to_bytes(2, byteorder='big', signed=True)

    @staticmethod
    def from_signed_int_to_unsigned_word(i):
        return i & 0xFFFF
