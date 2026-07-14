import argparse
import os
import sys

from Machine import build_machine
from Scripting import Scripting

parser = argparse.ArgumentParser(description="Z-Machine interpreter")
parser.add_argument("game", nargs="?", default="TRINITY.DAT",
                    help="game file to load (default: TRINITY.DAT)")
parser.add_argument("--ui", choices=["plain", "ansi", "curses", "qt"], default="qt",
                    help="display backend: plain (stdout), ansi, curses, qt GUI (default)")
parser.add_argument("--commands", metavar="FILE",
                    help="replay commands from file (plain list or transcript)")
parser.add_argument("--gameplay-dir", metavar="DIR", default=".",
                    help="directory for save/transcript/map artifacts (default: current directory)")
parser.add_argument("--seed", type=int, metavar="N",
                    help="seed the random number generator for deterministic replay")
parser.add_argument("--debug", action="store_true",
                    help="show debug windows (qt only)")
parser.add_argument("--undo-random-continue", action="store_true",
                    help="don't reset the RNG on undo (allows re-rolling random outcomes)")
parser.add_argument("--transcript", action="store_true",
                    help="start a transcript immediately, written to "
                         "<gameplay-dir>/transcript_<YYMMDD>_nn.txt")
args = parser.parse_args()

game_arg = args.game
if not os.path.exists(game_arg):
    candidate = os.path.join("..", "data", game_arg)
    if os.path.exists(candidate):
        game_arg = candidate

# --- select backend -------------------------------------------------------

def _make_screen(ui):
    if ui == "plain":
        from ScreenPlain import PlainScreen
        return PlainScreen()
    if ui == "ansi":
        from ScreenAnsi import AnsiScreen
        return AnsiScreen()
    if ui == "curses":
        try:
            import curses  # noqa: F401
        except ImportError:
            sys.exit("curses is not available.\n"
                     "On Windows install it with:  pip install windows-curses")
        from ScreenCurses import CursesScreen
        return CursesScreen()
    # default: qt
    from ScreenQt import ZMachineScreen
    return ZMachineScreen()

screen = _make_screen(args.ui)

if args.ui == "qt" and args.debug:
    screen._show_debug = True

screen.init()
screen._seed = args.seed

scripting = Scripting(args.commands) if args.commands else None
if scripting is not None:
    screen.auto_more = True
processor = build_machine(game_arg, screen, scripting=scripting, seed=args.seed,
                          gameplay_dir=args.gameplay_dir)
processor.instructions.undo_random_continue = args.undo_random_continue

if args.transcript:
    from Utils import Utils
    screen.open_transcript(Utils.next_transcript_path(processor.gameplay_dir))

# run() blocks until the game ends (each backend drives its own loop)
screen.run(processor)
