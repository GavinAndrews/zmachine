from array import array

from DictionaryTable import DictionaryTable
from Header import Header
from infocomm.AbbreviationTable import AbbreviationTable
from infocomm.ObjectTable import ObjectTable
from infocomm.Processor import Processor
from infocomm.Scripting import Scripting

fileName = "../data/TRINITY.DAT"
#fileName = "../data/ZORK1.DAT"

with open(fileName, mode='rb') as file:
    file_bytes = file.read()
    memory : array = array('B', file_bytes)
    # Bodge Config
    memory[1] |= 0x20
    # Bodge Interpreter Standard - Z Machine 1.1
    memory[50] = 0x01
    memory[51] = 0x01
    # Screen dimensions — Trinity checks these and refuses to start if too narrow
    memory[0x20] = 25   # screen height in lines
    memory[0x21] = 80   # screen width in characters


header = Header(memory)
game_version = header.ZVERSION_version

# Get the initial program counter from the header.
# For V1-5, bytes 6-7 are a plain byte address (not packed).
# Only V6+ stores the main routine as a packed address.
start = header.START

abbreviationTable = AbbreviationTable(start_location=header.FWORDS, memory=memory)

dictionary_table = DictionaryTable(header.VOCAB, memory, abbreviationTable,
                                   game_version=game_version)

objectTable = ObjectTable(start_location=header.OBJECT, memory=memory,
                          abbreviations=abbreviationTable,
                          game_version=game_version)

#scripting = Scripting("../script2")
scripting = None

# In Infocomm.py, where you create the Processor:

if game_version >= 4:
    # For V4+, let Processor create Globals with the fixed address
    processor = Processor(
        memory=memory,
        start=start,
        object_table=objectTable,
        abbreviation_table=abbreviationTable,
        dictionary=dictionary_table,
        scripting=scripting,
        filename=fileName,
        purbot=header.PURBOT,
        game_version=game_version
    )
else:
    # For V1-3, create Globals with the header address and pass to Processor
    from Globals import Globals
    global_variables = Globals(memory, game_version, header.GLOBALS)
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
        global_variables=global_variables  # You'll need to add this parameter
    )


while True:
    try:
        processor.next_instruction()
    except KeyboardInterrupt:
        print("\n[DEBUG] Interrupted by user")
        break
    except Exception as e:
        import traceback
        traceback.print_exc()
        break