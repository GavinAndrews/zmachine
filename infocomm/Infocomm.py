from Globals import Globals
from Header import Header
from Processor import Processor
from infocomm.AbbreviationTable import AbbreviationTable
from infocomm.ObjectTable import ObjectTable
from infocomm.PropertyTable import PropertyTable
from array import array

fileName = "../data/ZORK1.DAT"

with open(fileName, mode='rb') as file:  # b is important -> binary
    file_bytes = file.read()
    memory = array('B', file_bytes)

header = Header(memory)

global_variables = Globals(memory, header.GLOBALS)


abbreviationTable = AbbreviationTable(start_location=header.FWORDS, memory=memory)
# for i in range(0, 96):
#     print("|"+abbreviationTable.toString(i)+"|")

objectTable = ObjectTable(start_location=header.OBJECT, memory=memory, abbreviations=abbreviationTable)

# for i in range(1, 250+1):
#     obj = objectTable.find(i)
#     print(f"{i:3} \"{obj.description()}\"")
#     obj.dump_properties()

processor = Processor(memory=memory, start=header.START, global_variables=global_variables, object_table=objectTable, abbreviation_table=abbreviationTable)
for i in range(0, 128):
    processor.next_instruction()
