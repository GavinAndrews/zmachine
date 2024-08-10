from Utils import Utils


class PropertyTableEntry:
    def __init__(self, address, memory):
        self.address = address
        self.memory = memory

    @classmethod
    def decode_n_and_l(cls, prop):
        n = prop & 0x1F
        l = (prop >> 5) + 1
        return n, l

    def put_value(self, value):
        n, l = self.decode_n_and_l(self.memory[self.address])
        value_address = self.address+1
        if l == 1:
            Utils.mwrite_byte(self.memory, value_address, value)
        else:
            Utils.mwrite_word(self.memory, value_address, value)
