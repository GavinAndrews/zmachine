#!/usr/bin/env python
"""
Headless Z-Machine runner for automated testing.

Feeds a list of commands to the interpreter, captures all screen events,
and reports on the popup lifecycle and whether the poem appears only in the
upper window.

Usage (from infocomm/ directory):
    python RunHeadless.py TRINITY.DAT
    python RunHeadless.py TRINITY.DAT --commands "" "N" "SE" "EXAMINE SUNDIAL" ""
    python RunHeadless.py TRINITY.DAT --verbose

The default command sequence targets the sundial poem popup in Trinity:
    ""               key-press to dismiss the credits screen
    ""               key-press to dismiss the chapter-title screen
    "N"              first move
    "SE"             second move
    "EXAMINE SUNDIAL" trigger the poem popup
    ""               key-press to dismiss the popup

Exit code: 0 if poem appears ONLY in the upper window (popup correct), 1 otherwise.
"""
import os
import sys
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from Machine import build_machine
from HeadlessScreen import HeadlessScreen, StopExecution
from Instructions import _UndoPerformed

# Default command sequence for the Trinity sundial test
TRINITY_SUNDIAL = ['', '', 'N', 'SE', 'EXAMINE SUNDIAL', '']


class ListScripting:
    """Feed a fixed list of strings as interpreter input.

    Each call to get_line() returns the next string (or None when exhausted).
    Used for both read_line (full command) and read_char (first character).
    """
    def __init__(self, commands):
        self._lines = list(commands)
        self._pos   = 0

    def get_line(self):
        if self._pos < len(self._lines):
            line = self._lines[self._pos]
            self._pos += 1
            return line
        return None     # exhausted → caller falls through to screen.read_line/read_char


def run(game_path, commands, seed=None, max_steps=2_000_000):
    """Run the interpreter headlessly.  Returns (HeadlessScreen, steps_executed)."""
    scripting = ListScripting(commands)
    screen    = HeadlessScreen()
    screen.init()

    processor = build_machine(game_path, screen, scripting=scripting, seed=seed)

    steps = 0
    while steps < max_steps:
        try:
            processor.next_instruction()
        except StopExecution:
            break
        except _UndoPerformed:
            pass
        except SystemExit:
            break
        except Exception as exc:
            print(f'[FATAL at step {steps}]: {exc}', file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            break
        steps += 1

    return screen, steps


# ------------------------------------------------------------------
# Reporting
# ------------------------------------------------------------------

POEM_MARKER = "Lewis Carroll"   # unambiguous phrase; no Z-machine special-quote characters


def _find_poem(text):
    return POEM_MARKER.lower() in text.lower()


def report(screen, steps, verbose=False):
    popup         = screen.popup_events()
    poem_in_upper = _find_poem(screen.upper_text())
    poem_in_lower = _find_poem(screen.lower_text())

    print(f'Executed {steps:,} instructions, {len(screen.events)} screen events')
    print()

    if popup:
        print('=== POPUP LIFECYCLE ===')
        for e in popup:
            if e.type == 'print':
                text = repr(e.kwargs['text'])
                if len(text) > 74:
                    text = text[:70] + "...'"
                win  = e.kwargs['win']
                mark = ' <- LEAK' if win == 0 and _find_poem(e.kwargs['text']) else ''
                print(f"  [W{win}] {text}{mark}")
            else:
                print(f"  [{e.type.upper()}] {e.kwargs}")
        print()
    else:
        print('(no popup/split-window detected)')
        print()

    print('=== VERIFICATION ===')
    print(f'  Poem in upper window (popup) : {"YES  [OK]"   if poem_in_upper else "NO   [FAIL]"}')
    print(f'  Poem in lower window (leak)  : {"YES  [FAIL]" if poem_in_lower else "NO   [OK]"}')
    print()

    if verbose:
        print('=== ALL EVENTS ===')
        print(screen.format_summary())
        print()

    ok = poem_in_upper and not poem_in_lower
    print('RESULT:', 'PASS' if ok else 'FAIL')
    return ok


def main():
    parser = argparse.ArgumentParser(
        description='Headless Z-Machine runner — tests popup lifecycle')
    parser.add_argument('game', nargs='?', default='TRINITY.DAT',
                        help='game file (default: TRINITY.DAT)')
    parser.add_argument('--commands', nargs='*', default=None,
                        metavar='CMD',
                        help='command sequence (default: Trinity sundial sequence)')
    parser.add_argument('--seed', type=int, default=42,
                        help='RNG seed for deterministic replay (default: 42)')
    parser.add_argument('--steps', type=int, default=2_000_000,
                        help='max instruction steps (default: 2 000 000)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='print all screen events')
    args = parser.parse_args()

    game = args.game
    if not os.path.exists(game):
        candidate = os.path.join('..', 'data', game)
        if os.path.exists(candidate):
            game = candidate

    commands = args.commands if args.commands is not None else TRINITY_SUNDIAL

    print(f'Game     : {game}')
    print(f'Commands : {commands}')
    print(f'Seed     : {args.seed}')
    print()

    screen, steps = run(game, commands, seed=args.seed, max_steps=args.steps)
    ok = report(screen, steps, verbose=args.verbose)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
