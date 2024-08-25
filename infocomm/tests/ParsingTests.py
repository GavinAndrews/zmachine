import unittest

from array import array

from DictionaryTable import DictionaryTable
from Globals import Globals
from Header import Header
from ZStrings import convertToEncodedWords
from infocomm.AbbreviationTable import AbbreviationTable


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
        #str = "examine ghostsocks"
        str = "\""
        word = str.split(" ")[0]
        print(word)
        words = convertToEncodedWords(word)
        print(f"{[f'{x:04X}' for x in words]}")
        #self.assertEqual(abs(10), 10)

        result = self.dictionary_table.find_phrase(words)
        print(f"Result: {result}")

        if result is not None:
            dictionary_table_entry = self.dictionary_table.find(result)
            dictionary_table_entry.dump()
        else:
            print("Not in dictionary")


if __name__ == "__main__":
    unittest.main(verbosity=2)
