import unittest

from array import array

from infocomm.AbbreviationTable import AbbreviationTable
from infocomm.DictionaryTable import DictionaryTable
from infocomm.Globals import Globals
from infocomm.Header import Header
from infocomm.ZStrings import convertToEncodedWords


class ParsingTests(unittest.TestCase):

    def setUp(self):
        file_name = "../../data/ZORK1.DAT"

        with open(file_name, mode='rb') as file:  # b is important -> binary
            file_bytes = file.read()
            self.memory = array('B', file_bytes)

        self.header = Header(self.memory)

        global_variables = Globals(self.memory, self.header.GLOBALS)

        self.abbreviationTable = AbbreviationTable(start_location=self.header.FWORDS, memory=self.memory)
        # for i in range(0, 96):
        #     print("|"+abbreviationTable.toString(i)+"|")

        self.dictionary_table = DictionaryTable(self.header.VOCAB, self.memory, self.abbreviationTable)

    def test_parsing(self):
        """Parse String"""
        str = "examine,     ghostsocks"

        # Ensure we are in lowercase
        str = str.lower()

        separators = set(self.dictionary_table.get_seperators())
        space_in_separators = ' ' in separators
        if not space_in_separators:
            separators.add(" ")

        words = []
        start = 0
        current_word = ""
        for i, c in enumerate(str):
            if c in separators:
                print("SEP")
                if len(current_word) > 0:
                    words.append((start, current_word))
                    current_word = ""
                if c != ' ' or space_in_separators:
                    words.append((i, c))
                start = i + 1
            else:
                print("CHAR: {c}")
                current_word = current_word + c
        # Last Word
        if len(current_word) > 0:
            words.append((start, current_word))

        for start, word in words:
            print(f"Start:{start:3} Word:{word}")
            words = convertToEncodedWords(word)
            print(f"{[f'{x:04X}' for x in words]}")
            #self.assertEqual(abs(10), 10)

            result = self.dictionary_table.find_phrase(words)
            print(f"Result: {result}")

            if result is not None:
                dictionary_table_entry = self.dictionary_table.find(result)
                dictionary_table_entry.dump()
                print(f"Addr: {dictionary_table_entry.get_start_address():04X}")
            else:
                print("Not in dictionary")


if __name__ == "__main__":
    unittest.main(verbosity=2)
