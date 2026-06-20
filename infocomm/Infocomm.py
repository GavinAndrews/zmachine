import argparse
import os
from array import array

from DictionaryTable import DictionaryTable
from Header import Header
from AbbreviationTable import AbbreviationTable
from ObjectTable import ObjectTable
from Processor import Processor
from Scripting import Scripting
from Instructions import _UndoPerformed
from Screen import Screen

parser = argparse.ArgumentParser(description="Z-Machine interpreter")
parser.add_argument("game", nargs="?", default="TRINITY.DAT",
                    help="game file to load (default: TRINITY.DAT)")
parser.add_argument("--commands", metavar="FILE",
                    help="replay commands from file (plain list or transcript)")
parser.add_argument("--seed", type=int, metavar="N",
                    help="seed the random number generator for deterministic replay")
args = parser.parse_args()

# Accept bare name (e.g. ZORK1.DAT), name relative to ../data/, or full path
game_arg = args.game
if not os.path.exists(game_arg):
    candidate = os.path.join("..", "data", game_arg)
    if os.path.exists(candidate):
        game_arg = candidate

fileName = game_arg

screen = Screen()
screen.init()

with open(fileName, mode='rb') as file:
    file_bytes = file.read()
    memory: array = array('B', file_bytes)
    memory[50] = 0x01          # Z-Machine standard 1.1
    memory[51] = 0x01

rows, cols = screen.get_size()
memory[0x20] = rows
memory[0x21] = cols

header = Header(memory)
game_version = header.ZVERSION_version

# Set capability flags so the game knows what we support
if game_version >= 4:
    # Clear V3 split-screen bit (0x20); set bold (0x04), emphasis (0x08),
    # fixed-width (0x10), timed input (0x80)
    memory[1] = (memory[1] & ~0x20) | 0x04 | 0x08 | 0x10 | 0x80
if game_version >= 5:
    memory[0] |= 0x01   # colour support

# V1-5: bytes 6-7 are a plain byte address (not packed).
start = header.START

abbreviationTable = AbbreviationTable(start_location=header.FWORDS, memory=memory)
dictionary_table  = DictionaryTable(header.VOCAB, memory, abbreviationTable, game_version=game_version)
objectTable       = ObjectTable(start_location=header.OBJECT, memory=memory,
                                abbreviations=abbreviationTable, game_version=game_version)

scripting = Scripting(args.commands) if args.commands else None

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
    screen=screen,
)

if args.seed is not None:
    processor.instructions.random = args.seed & 0x7FFFFFFF

try:
    while True:
        try:
            processor.next_instruction()
        except _UndoPerformed:
            pass   # state already restored; re-execute from saved PC
        except KeyboardInterrupt:
            screen.reset()
            print("\n[Interrupted]")
            break
        except SystemExit:
            break
        except Exception:
            import traceback
            traceback.print_exc()
            break
finally:
    screen.reset()
