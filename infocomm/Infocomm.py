from array import array

from DictionaryTable import DictionaryTable
from Globals import Globals
from Header import Header
from Processor import Processor
from infocomm.AbbreviationTable import AbbreviationTable
from infocomm.ObjectTable import ObjectTable

fileName = "../data/ZORK1.DAT"

with open(fileName, mode='rb') as file:  # b is important -> binary
    file_bytes = file.read()
    memory = array('B', file_bytes)

header = Header(memory)

global_variables = Globals(memory, header.GLOBALS)

abbreviationTable = AbbreviationTable(start_location=header.FWORDS, memory=memory)
# for i in range(0, 96):
#     print("|"+abbreviationTable.toString(i)+"|")

dictionary_table = DictionaryTable(header.VOCAB, memory, abbreviationTable)

# for i in range(1, dictionary_table.get_word_count() + 1):
#     dictionary_table_entry = dictionary_table.find(i)
#     dictionary_table_entry.dump()

objectTable = ObjectTable(start_location=header.OBJECT, memory=memory, abbreviations=abbreviationTable)

# for i in range(1, 250+1):
#     obj = objectTable.find(i)
#     print(f"{i:3} \"{obj.description()}\"")
#     obj.dump_properties()

processor = Processor(memory=memory, start=header.START, global_variables=global_variables, object_table=objectTable,
                      abbreviation_table=abbreviationTable, dictionary=dictionary_table)
while True:
    processor.next_instruction()
