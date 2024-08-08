from infocomm.ZStrings import toZString


class DictionaryTableEntry:
    def __init__(self, start_location, memory, entry_length, abbreviations):
        self.start_location = start_location
        self.memory = memory
        self.entry_length = entry_length
        self.abbreviations = abbreviations

    def dump(self):
        print(f"{self.start_location:04X}", end="")
        for i in range(0, self.entry_length):
            print(f" {self.memory[self.start_location+i]:02X}", end="")
        print(" "+toZString(self.start_location, self.memory, self.abbreviations, count=2))

