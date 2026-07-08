"""
ScreenPlain.py — Plain stdout/stdin backend.

No cursor positioning, no split-window display.  Upper-window content
(status bar, popups) is silently dropped; only lower-window text is shown.
Works everywhere with no extra dependencies.
"""

import sys
from ScreenBase import ScreenBase


def _getch():
    """Read one character from stdin without waiting for Enter."""
    if sys.platform == 'win32':
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ('\x00', '\xe0'):   # function/extended key prefix — skip both bytes
            msvcrt.getwch()
            return '\r'
        return ch
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return ch


class PlainScreen(ScreenBase):
    """Streams lower-window output to stdout; reads input with system line editing."""

    def __init__(self):
        super().__init__()
        self._current_win = 0

    def init(self):
        pass

    def reset(self):
        if self.transcript_file:
            self.close_transcript()

    # ------------------------------------------------------------------
    # Output — lower window only; upper window is suppressed
    # ------------------------------------------------------------------

    def print_str(self, s: str):
        if self._current_win != 0:
            return                   # silently discard upper-window text
        sys.stdout.write(s)
        sys.stdout.flush()
        if self.stream2_active and self.transcript_file:
            self.transcript_file.write(s)

    def set_window(self, win: int):
        self._current_win = win

    def erase_window(self, win: int):
        self._current_win = 0       # always fall back to lower

    def update_status_line(self, location: str, right_text: str):
        width = 79
        left = (location or "")[:width]
        pad = max(1, width - len(left) - len(right_text))
        sys.stdout.write(f"[{left}{' ' * pad}{right_text}]\n")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def read_line(self, max_chars: int, time_tenths: int = 0,
                  time_routine_cb=None) -> str:
        try:
            line = input()
        except EOFError:
            line = ''
        return line[:max_chars - 1]

    def read_char(self, time_tenths: int = 0, time_routine_cb=None) -> str:
        return _getch()

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------

    def run(self, processor):
        self._run_loop(processor)
