from array import array


class Header:
    def __init__(self, memory: array) -> None:
        self.ZVERSION_version = int.from_bytes(memory[0:1], 'little')
        self.ZVERSION_mode = memory[1]
        self.ZORKID = int.from_bytes(memory[2:4], 'big')
        self.ENDLOD = int.from_bytes(memory[4:6], 'big')
        self.START = int.from_bytes(memory[6:8], 'big')
        self.VOCAB = int.from_bytes(memory[8:10], 'big')
        self.OBJECT = int.from_bytes(memory[10:12], 'big')
        self.GLOBALS = int.from_bytes(memory[12:14], 'big')
        self.PURBOT = int.from_bytes(memory[0x000E:0x0010], 'big')
        self.FLAGS = memory[16:18]
        self.SERIAL = memory[18:24]
        self.FWORDS = int.from_bytes(memory[0x0018:0x0018 + 2], 'big')
        self.PLENTH = int.from_bytes(memory[26:28], 'big')
        self.PCHKSUM = int.from_bytes(memory[28:30], 'big')


    def dump(self) -> None:
        print(self.ZVERSION_version, self.ZVERSION_mode)
        print(self.ZORKID)
        print(self.ENDLOD)
        print(self.START)
        print(f"VOCAB: {self.VOCAB:04X}")
        print(f"OBJECT: {self.OBJECT:04X}")
        print(f"GLOBALS: {self.GLOBALS:04X}")
        print(f"PURBOT: {self.PURBOT:04X}")

        print(self.FLAGS)
        print(self.SERIAL)
        print(f"FWORDS: {self.FWORDS:04X}")  # AKA Abbreviations
        print(f"PLENTH: {self.PLENTH:04X}")
        print(f"PCHKSUM: {self.PCHKSUM:04X}")
