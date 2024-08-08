class Utils:
    @staticmethod
    def mread_word(memory, offset):
        return int.from_bytes(memory[offset:offset+2], 'big')
