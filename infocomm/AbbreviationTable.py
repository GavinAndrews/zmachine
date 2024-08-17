from infocomm.ZStrings import toZString


class AbbreviationTable:
    def __init__(self, start_location, memory):
        self.startLocation = start_location
        self.memory = memory

    def toString(self, n):
        location = self.startLocation + n * 2
        address = int.from_bytes(self.memory[location:location + 2], 'big') * 2
        return toZString(address, self.memory, self, None)
