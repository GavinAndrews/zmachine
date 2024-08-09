from Utils import Utils


class Globals:
    def __init__(self, memory, start_location):
        self.memory = memory
        self.start_location = start_location

    def read_global(self, global_number):
        location = self.start_location + global_number * 2
        w = Utils.mread_word(self.memory, location)
        return w

    def write_global(self, global_number, value):
        location = self.start_location + global_number * 2
        self.memory[location] = value >> 8
        self.memory[location + 1] = value & 0xFF

    def dump(self):
        for i in range(0, 240):
            w = self.read_global(i)
            print(
                f"{self.start_location:05X} {self.memory[self.start_location + i * 2]:02X} {self.memory[self.start_location + i * 2 + 1]:02X}                    G{i:02X}, , Global #{i + 1:<3} =   0x{w:04X}")
