from infocomm.DictionaryTableEntry import DictionaryTableEntry


class DictionaryTable:
    def __init__(self, start_location, memory, abbreviations):
        self.header_start = start_location
        self.memory = memory
        self.abbreviations = abbreviations

        self.num_separators = memory[start_location]
        print(f"{start_location:04X} {self.num_separators:02X}")
        start_location += 1

        self.separators = memory[start_location: start_location + self.num_separators]

        start_location += self.num_separators

        print(f"{start_location:04X}", end="")
        for b in self.separators:
            print(f" {b:02X}", end="")
        print()

        self.entry_length = memory[start_location]
        print(f"{start_location:04X} {self.entry_length:02X}                     {self.entry_length:3} entry size")
        start_location += 1

        self.word_count = int.from_bytes(self.memory[start_location:start_location + 2], 'big')
        print(
            f"{start_location:04X} {memory[start_location]:02X} {memory[start_location + 1]:02X}                {self.word_count:5} word count")
        start_location += 2

        self.dictionary_start = start_location
        print(f"{self.dictionary_start:04X}                            Dict Start")

    def get_seperators(self):
        return [chr(s) for s in self.separators]

    def get_word_count(self):
        return self.word_count

    def find(self, n):
        return DictionaryTableEntry(self.dictionary_start + (n - 1) * self.entry_length, self.memory,
                                    self.entry_length, self.abbreviations)
