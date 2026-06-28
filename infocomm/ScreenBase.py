"""
ScreenBase.py — Abstract base class for all Z-machine screen backends.

Every backend (plain, ansi, curses, qt, headless) inherits from this class.
"""

import sys
from abc import ABC, abstractmethod


class ScreenBase(ABC):

    def __init__(self):
        self.processor       = None
        self.stream2_active  = False
        self.transcript_file = None
        self.auto_more       = False  # suppress [More] pauses during scripted replay
        self.current_fg      = -1
        self.current_bg      = -1
        self._seed           = None   # stored for restart

    # ------------------------------------------------------------------
    # Lifecycle — must override
    # ------------------------------------------------------------------

    @abstractmethod
    def init(self): ...

    @abstractmethod
    def reset(self): ...

    @abstractmethod
    def run(self, processor): ...

    # ------------------------------------------------------------------
    # Output — must override print_str at minimum
    # ------------------------------------------------------------------

    @abstractmethod
    def print_str(self, s: str): ...

    def print_char(self, ch: str):     self.print_str(ch)
    def new_line(self):                self.print_str('\n')
    def append_text(self, t, **_kw):  self.print_str(t)
    def refresh(self):                 pass

    # ------------------------------------------------------------------
    # Window management — backends override what they support
    # ------------------------------------------------------------------

    def split_window(self, height: int):       pass
    def set_window(self, win: int):            pass
    def set_cursor(self, row: int, col: int):  pass
    def get_cursor(self):                       return (1, 1)
    def set_text_style(self, style: int):      pass
    def set_colour(self, fg: int, bg: int):
        self.current_fg = fg
        self.current_bg = bg
    def erase_window(self, win: int):          pass
    def erase_line(self):                      pass
    def update_status_line(self, loc, score, turns): pass
    def print_location_prompt(self, loc_text):
        self.print_str(f'\n{loc_text}\n> ')

    # ------------------------------------------------------------------
    # Input — must override
    # ------------------------------------------------------------------

    @abstractmethod
    def read_line(self, max_chars: int, time_tenths: int = 0,
                  time_routine_cb=None) -> str: ...

    @abstractmethod
    def read_char(self, time_tenths: int = 0, time_routine_cb=None) -> str: ...

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def get_size(self):
        return (25, 80)

    def transcript_write(self, s):
        """Write directly to the transcript without rendering to screen."""
        if self.stream2_active and self.transcript_file:
            self.transcript_file.write(s)

    def open_transcript(self, path=None):
        if self.transcript_file:
            return
        path = path or 'transcript.txt'
        self.transcript_file = open(path, 'a', encoding='utf-8')
        self.stream2_active  = True
        self.print_str(f"\n[Transcript started: {path}]\n")

    def close_transcript(self):
        self.stream2_active = False
        if self.transcript_file:
            self.transcript_file.flush()
            self.transcript_file.close()
            self.transcript_file = None
        self.print_str("\n[Transcript ended]\n")

    # ------------------------------------------------------------------
    # Shared synchronous run loop for plain / ansi / curses backends
    # ------------------------------------------------------------------

    def _run_loop(self, processor):
        """Drive processor.next_instruction() in a tight synchronous loop."""
        from Instructions import _UndoPerformed, _RestartRequested
        from Machine import build_machine

        while True:
            try:
                processor.next_instruction()
            except _UndoPerformed:
                pass
            except _RestartRequested:
                undo_rc = processor.instructions.undo_random_continue
                self.erase_window(-1)
                processor = build_machine(
                    processor.filename, self,
                    scripting=None,
                    seed=self._seed,
                )
                processor.instructions.undo_random_continue = undo_rc
            except SystemExit:
                break
            except KeyboardInterrupt:
                break
            except Exception:
                import traceback
                traceback.print_exc(file=sys.stderr)
                break
