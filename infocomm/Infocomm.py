from array import array

from DictionaryTable import DictionaryTable
from Header import Header
from AbbreviationTable import AbbreviationTable
from ObjectTable import ObjectTable
from Processor import Processor
from Scripting import Scripting

fileName = "../data/TRINITY.DAT"
#fileName = "../data/ZORK1.DAT"

with open(fileName, mode='rb') as file:
    file_bytes = file.read()
    memory: array = array('B', file_bytes)
    memory[1] |= 0x20          # interpreter flags
    memory[50] = 0x01          # Z-Machine standard 1.1
    memory[51] = 0x01
    memory[0x20] = 25          # screen height
    memory[0x21] = 80          # screen width

header = Header(memory)
game_version = header.ZVERSION_version

# V1-5: bytes 6-7 are a plain byte address (not packed).
start = header.START

abbreviationTable = AbbreviationTable(start_location=header.FWORDS, memory=memory)
dictionary_table  = DictionaryTable(header.VOCAB, memory, abbreviationTable, game_version=game_version)
objectTable       = ObjectTable(start_location=header.OBJECT, memory=memory,
                                abbreviations=abbreviationTable, game_version=game_version)

#scripting = Scripting("../script2")
scripting = None

processor = Processor(
    memory=memory,
    start=start,
    object_table=objectTable,
    abbreviation_table=abbreviationTable,
    dictionary=dictionary_table,
    scripting=scripting,
    filename=fileName,
    purbot=header.PURBOT,
    game_version=game_version,
)

while True:
    try:
        processor.next_instruction()
    except KeyboardInterrupt:
        print("\n[Interrupted]")
        break
    except Exception:
        import traceback
        traceback.print_exc()
        break
