# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Z-Machine interpreter written in Python that runs classic Infocom interactive fiction games (Zork I/II/III, Trinity). Implements the Z-Machine virtual machine spec (versions 1–5+).

Reference specs: `zmach06e.pdf` (Z-Machine spec), `spec-zip.pdf` (Quetzal save format).
Online spec: https://zspec.jaredreisinger.com/

## Running

All source lives in `infocomm/`. Run the interpreter from that directory:

```bash
cd infocomm
python Infocomm.py
```

The game file is hardcoded at the top of `Infocomm.py` — switch between `ZORK1.DAT` and `TRINITY.DAT` by commenting/uncommenting. To use a script file for automated input, uncomment the `scripting` line and pass a script path.

## Tests

Tests use `unittest` and live in `infocomm/tests/`. Run from the project root:

```bash
cd infocomm/tests
python -m unittest ParsingTests
```

Tests load `../../data/ZORK1.DAT` relative to their location.

## Architecture

The interpreter is a single-threaded fetch-decode-execute loop (`Processor.next_instruction()` called in a `while True` in `Infocomm.py`).

**Startup (`Infocomm.py`):**
- Loads game file as a mutable `array('B')` byte array
- Applies header patches (interpreter flags, screen dimensions)
- Constructs all subsystems and passes them into `Processor`

**Core execution (`Processor.py`):**
- Decodes opcode form (LONG/SHORT/VARIABLE) and operand types from the instruction stream
- Dispatches to handler methods in `Instructions.py`
- Manages the program counter (`self.pc`) and local/global variable access

**Memory model:**
- The `memory` array is shared and mutated in-place by all components — there is no separate bus or address space abstraction
- `Globals.py` provides named access to global variables via their header-defined base address
- `Stack.py` implements the 1024-word call stack; stack frames track locals and return addresses

**Game data tables** (all parse directly from `memory` at their header-specified offsets):
- `Header.py` — parses the 64-byte file header; all offsets and flags come from here
- `ObjectTable.py` / `ObjectTableEntry.py` / `PropertyTable.py` / `PropertyTableEntry.py` — object tree with attributes and properties
- `DictionaryTable.py` / `DictionaryTableEntry.py` — vocabulary for input tokenisation
- `AbbreviationTable.py` — 96-entry table used by string decoding

**String handling (`ZStrings.py`):**
- Decodes Z-encoded strings (5-bit characters packed into 2-byte words)
- Three alphabets (A0/A1/A2) plus ZSCII escapes and abbreviation expansion

**Save/restore (`Quetzal.py`):**
- Implements the Quetzal IFF-based save format
- Stores compressed memory delta (CMEM), call stack (STKS), and game ID (IFHD)

**Debugging aids:**
- `TraceFile.py` — reads Frotz interpreter trace files for step-by-step comparison
- `Scripting.py` — feeds pre-recorded command sequences as player input

## Key Conventions

- Version branching: many functions check `game_version` (1–3 vs 4+) for packed-address arithmetic, object table layout, and globals addressing
- V1–5: PC start address (header bytes 6–7) is a plain byte address. Only V6+ stores it as a packed address (main routine). Routine *call* addresses in instructions are always packed (×2 for V1–3, ×4 for V4–7)
- V1–4: routine headers store initial local-variable values (2 bytes each, after the count byte). V5+: no stored values, locals start as 0
- Imports use bare module names (not package-qualified) when run from inside `infocomm/`; tests use `infocomm.` prefix
