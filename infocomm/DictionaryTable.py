import bisect
from collections import UserList

from infocomm.DictionaryTableEntry import DictionaryTableEntry
from infocomm.Utils import Utils


class DictionaryTable:
    def __init__(self, start_location, memory, abbreviations):
        self.header_start = start_location
        self.memory = memory
        self.abbreviations = abbreviations

        self.num_separators = memory[start_location]
        start_location += 1

        self.separators = memory[start_location: start_location + self.num_separators]

        start_location += self.num_separators

        self.entry_length = memory[start_location]
        start_location += 1

        self.word_count = int.from_bytes(self.memory[start_location:start_location + 2], 'big')
        start_location += 2

        self.dictionary_start = start_location

        self.dictionary_entry_key_words = 2   # V1-3... Later 3

        self.dictionary_keys = DictionaryKeys(self.memory, self.dictionary_start, self.word_count, self.entry_length, self.dictionary_entry_key_words)

    def dump(self):
        print(f"{self.start_location:04X} {self.num_separators:02X}")
        print(f"{self.start_location:04X}", end="")
        for b in self.separators:
            print(f" {b:02X}", end="")
        print()
        print(f"{self.start_location:04X} {self.entry_length:02X}                     {self.entry_length:3} entry size")
        print(
            f"{self.start_location:04X} {self.memory[self.start_location]:02X} {self.memory[self.start_location + 1]:02X}                {self.word_count:5} word count")
        print(f"{self.dictionary_start:04X}                            Dict Start")

    def get_seperators(self):
        return [chr(s) for s in self.separators]

    def get_word_count(self):
        return self.word_count

    def find(self, n):
        return DictionaryTableEntry(self.dictionary_start + (n - 1) * self.entry_length, self.memory,
                                    self.entry_length, self.abbreviations)

    def find_phrase(self, words):
        lower = 1
        higher = self.word_count
        i = bisect.bisect_left(self.dictionary_keys, words)
        if self.dictionary_keys[i] == DictionaryKey(words):
            return i
        else:
            return None


class DictionaryKey(UserList):
    def __init__(self, words):
        super().__init__(words)

    def __repr__(self):
        return f"DictionaryKey({self.data})"


class DictionaryKeys:
    def __init__(self, memory, dictionary_start, word_count, entry_length, dictionary_entry_key_words):
        self.memory = memory
        self.dictionary_start = dictionary_start
        self.word_count = word_count
        self.entry_length = entry_length
        self.dictionary_entry_key_words = dictionary_entry_key_words

    def __getitem__(self, index):
        memory_address = self.dictionary_start + (index - 1) * self.entry_length
        words = []
        for _ in range(self.dictionary_entry_key_words):
            word = Utils.mread_word(self.memory, memory_address)
            memory_address += 2
            words.append(word)
        return DictionaryKey(words)

    def __len__(self):
        return self.word_count
