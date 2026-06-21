import argparse
import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from Machine import build_machine
from Scripting import Scripting
from Instructions import _UndoPerformed, _RestartRequested
from Screen import ZMachineScreen

parser = argparse.ArgumentParser(description="Z-Machine interpreter")
parser.add_argument("game", nargs="?", default="TRINITY.DAT",
                    help="game file to load (default: TRINITY.DAT)")
parser.add_argument("--commands", metavar="FILE",
                    help="replay commands from file (plain list or transcript)")
parser.add_argument("--seed", type=int, metavar="N",
                    help="seed the random number generator for deterministic replay")
parser.add_argument("--debug", action="store_true",
                    help="show debug windows (object state, globals, stack)")
args = parser.parse_args()

game_arg = args.game
if not os.path.exists(game_arg):
    candidate = os.path.join("..", "data", game_arg)
    if os.path.exists(candidate):
        game_arg = candidate

app = QApplication(sys.argv)

screen = ZMachineScreen()
screen.init()

if args.debug:
    screen.debug_window.show()
    screen.object_window.show()
    screen.globals_window.show()
    screen.stack_window.show()

scripting = Scripting(args.commands) if args.commands else None

processor = build_machine(game_arg, screen, scripting=scripting, seed=args.seed)

if args.debug:
    screen.object_window.processor  = processor
    screen.globals_window.processor = processor
    screen.stack_window.processor   = processor

running = True


def run_step():
    global running, processor
    if not running:
        return
    try:
        processor.next_instruction()
    except _UndoPerformed:
        pass
    except _RestartRequested:
        # Reload the game from disk and start fresh inside the same window.
        screen.terminal.erase_window(-1)
        processor = build_machine(game_arg, screen, scripting=None, seed=args.seed)
        if args.debug:
            screen.object_window.processor  = processor
            screen.globals_window.processor = processor
            screen.stack_window.processor   = processor
    except KeyboardInterrupt:
        screen.reset()
        print("\n[Interrupted]")
        running = False
        app.quit()
    except SystemExit:
        running = False
        app.quit()
    except Exception:
        import traceback
        traceback.print_exc()
        running = False
        app.quit()

    if running:
        QTimer.singleShot(1, run_step)


QTimer.singleShot(10, run_step)

try:
    screen.exec()
except Exception:
    pass
finally:
    screen.reset()
    running = False
