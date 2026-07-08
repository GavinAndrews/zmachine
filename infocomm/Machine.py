"""Shared Z-machine construction: usable from both the Qt GUI and the headless runner."""
import os
from array import array

from Header import Header
from AbbreviationTable import AbbreviationTable
from DictionaryTable import DictionaryTable
from ObjectTable import ObjectTable
from Processor import Processor


def build_machine(game_path, screen, scripting=None, seed=None, gameplay_dir=None):
    """Load game_path, patch interpreter header bytes, wire up all subsystems.

    gameplay_dir is where save/transcript/map artifacts default to (see
    Utils.resolve_gameplay_path); it defaults to the current directory and is
    created if it doesn't exist.

    Returns the ready-to-run Processor.  screen.processor is also set.
    The caller is responsible for driving the main loop.
    """
    with open(game_path, 'rb') as fh:
        memory = array('B', fh.read())

    # Standard revision number (1.1) at 0x32-0x33
    memory[0x32] = 0x01
    memory[0x33] = 0x01

    # Screen dimensions the game can query
    memory[0x20] = 25   # height in lines
    memory[0x21] = 80   # width in chars

    # Interpreter capability flags — these bytes are zeroed in the .dat file
    # and must be filled in by the interpreter before the game starts running.
    # Queried from the screen backend so we never advertise a feature (e.g.
    # bold, or timed input) that the chosen --ui backend can't actually
    # deliver.
    game_version = memory[0]   # byte 0 is the version number directly
    if game_version >= 4:
        flags = 0
        if getattr(screen, 'supports_bold', False):        flags |= 0x04
        if getattr(screen, 'supports_italic', False):       flags |= 0x08
        if getattr(screen, 'supports_fixed_width', False):  flags |= 0x10
        if getattr(screen, 'supports_timed_input', False):  flags |= 0x80
        memory[0x01] |= flags
        memory[0x1C] = 6          # interpreter number: IBM PC
        memory[0x1D] = ord('F')  # interpreter version letter
    elif game_version <= 3:
        # Flags 1 (0x01): screen-splitting available (5)
        memory[0x01] |= 0x20

    header = Header(memory)
    game_version = header.ZVERSION_version

    abbrevs    = AbbreviationTable(start_location=header.FWORDS, memory=memory)
    dictionary = DictionaryTable(header.VOCAB, memory, abbrevs, game_version=game_version)
    obj_table  = ObjectTable(start_location=header.OBJECT, memory=memory,
                             abbreviations=abbrevs, game_version=game_version)

    processor = Processor(
        memory=memory,
        start=header.START,
        object_table=obj_table,
        abbreviation_table=abbrevs,
        dictionary=dictionary,
        scripting=scripting,
        filename=game_path,
        purbot=header.PURBOT,
        game_version=game_version,
        screen=screen,
    )

    if seed is not None:
        processor.instructions.random = seed & 0x7FFFFFFF

    gameplay_dir = os.path.abspath(gameplay_dir or os.getcwd())
    os.makedirs(gameplay_dir, exist_ok=True)
    processor.gameplay_dir = gameplay_dir
    screen.processor = processor
    return processor
