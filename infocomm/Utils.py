from array import array


class Utils:
    @staticmethod
    def mread_word(memory: array, offset: int) -> int:
        return int.from_bytes(memory[offset:offset + 2], 'big', signed=False)

    @staticmethod
    def mread_byte(memory: array, offset: int) -> int:
        return int(memory[offset])

    @staticmethod
    def mwrite_word(memory: array, offset: int, value: int) -> None:
        memory[offset] = (value >> 8) & 0xFF
        memory[offset + 1] = value & 0xFF

    @staticmethod
    def mwrite_byte(memory: array, offset: int, value: int) -> None:
        memory[offset] = value & 0xFF

    @staticmethod
    def from_unsigned_word_to_signed_int(i: int) -> int:
        return i if i < 32668 else i - 65536

    @staticmethod
    def from_signed_int_to_bytes(i: int) -> bytes:
        return i.to_bytes(2, byteorder='big', signed=True)

    @staticmethod
    def from_signed_int_to_unsigned_word(i: int) -> int:
        return i & 0xFFFF
