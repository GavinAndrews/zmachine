"""
ScreenAnsi.py — ANSI escape-code terminal backend.

Uses the alternate screen buffer so the game display doesn't mix with the
shell's scrollback.  The full 25×80 grid is repainted after every write,
which keeps the implementation simple and the display always correct.

Works in any ANSI-capable terminal: Windows Terminal, VSCode, xterm, etc.
Does NOT work in bare Windows Command Prompt (cmd.exe without VT enabled).
"""

import os
import sys
import time
from contextlib import contextmanager
from ScreenBase import ScreenBase
from ScreenGrid import ScreenGrid, ROWS, COLS, STYLE_REVERSE, STYLE_BOLD, STYLE_EMPHASIS, format_status_bar


# --- portable single-char read -------------------------------------------

def _getch():
    if sys.platform == 'win32':
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ('\x00', '\xe0'):
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


def _key_ready(timeout):
    """True if a keypress becomes available within `timeout` seconds."""
    if sys.platform == 'win32':
        import msvcrt
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if msvcrt.kbhit():
                return True
            time.sleep(0.02)
        return False
    else:
        import select
        r, _, _ = select.select([sys.stdin], [], [], max(0, timeout))
        return bool(r)


def _read_raw_char(fd):
    """Read one already-available byte from a fd already in raw mode (POSIX)."""
    ch = os.read(fd, 1).decode(errors='replace')
    if ch in ('\x00', '\xe0'):
        os.read(fd, 1)
        return '\r'
    return ch


@contextmanager
def _timed_input_mode(active):
    """On POSIX, hold the terminal in raw mode for the whole timed read so
    select()-based polling sees individual keystrokes as they arrive
    (normal per-keystroke _getch() toggles raw mode on and off between
    calls, which starves select() in cooked mode). No-op on Windows, where
    msvcrt.kbhit()/getwch() already work per-keystroke without this."""
    if active and sys.platform != 'win32':
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setraw(fd)
        try:
            yield
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    else:
        yield


def _getch_raw():
    """Read one keystroke already known to be available (see _key_ready)."""
    if sys.platform == 'win32':
        return _getch()
    return _read_raw_char(sys.stdin.fileno())


# --- ANSI helpers ---------------------------------------------------------

_RESET   = '\033[0m'
_REVERSE = '\033[7m'
_BOLD    = '\033[1m'
_ULINE   = '\033[4m'
_HIDE    = '\033[?25l'
_SHOW    = '\033[?25h'
_ALT_ON  = '\033[?1049h'   # enter alternate screen
_ALT_OFF = '\033[?1049l'   # leave alternate screen

def _pos(r, c):            # 1-indexed
    return f'\033[{r};{c}H'

def _style(s):
    out = _RESET
    if s & STYLE_REVERSE:  out += _REVERSE
    if s & STYLE_BOLD:     out += _BOLD
    if s & STYLE_EMPHASIS: out += _ULINE
    return out


class AnsiScreen(ScreenBase):
    supports_bold        = True
    supports_italic      = True
    supports_timed_input = True

    def __init__(self):
        super().__init__()
        self._sg = ScreenGrid()
        self._status_left  = None
        self._status_right = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init(self):
        # Enable ANSI on Windows if needed
        if sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.kernel32.SetConsoleMode(
                    ctypes.windll.kernel32.GetStdHandle(-11), 7)
            except Exception:
                pass
        sys.stdout.write(_ALT_ON + '\033[2J')
        sys.stdout.flush()

    def reset(self):
        if self.transcript_file:
            self.close_transcript()
        sys.stdout.write(_ALT_OFF)
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Full repaint — called after every grid change
    # ------------------------------------------------------------------

    def _render(self):
        sg = self._sg
        offset = 1 if self._status_left is not None else 0
        out = [_HIDE]
        if offset:
            bar = format_status_bar(self._status_left, self._status_right)
            out.append(_pos(1, 1))
            out.append(_style(STYLE_REVERSE))
            out.append(bar)
            out.append(_RESET)
        cur_style = -1
        for r in range(ROWS):
            out.append(_pos(r + 1 + offset, 1))
            for c in range(COLS):
                cell = sg._grid[r][c]
                if cell.style != cur_style:
                    cur_style = cell.style
                    out.append(_style(cur_style))
                out.append(cell.char)
        out.append(_RESET)
        # Place terminal cursor at lower-window input position
        out.append(_pos(sg._lo_row + 1 + offset, sg._lo_col + 1))
        out.append(_SHOW)
        sys.stdout.write(''.join(out))
        sys.stdout.flush()

    def update_status_line(self, location: str, right_text: str):
        self._status_left  = location
        self._status_right = right_text
        self._render()

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def print_str(self, s: str):
        self._sg.print_str(s)
        self._render()
        if self.stream2_active and self.transcript_file:
            self.transcript_file.write(s)

    def split_window(self, height: int):
        self._sg.split_window(height)
        self._render()

    def set_window(self, win: int):
        self._sg.set_window(win)

    def set_cursor(self, row: int, col: int):
        self._sg.set_cursor(row, col)

    def get_cursor(self):
        return self._sg.get_cursor()

    def set_text_style(self, style: int):
        self._sg.set_text_style(style)

    def erase_window(self, win: int):
        self._sg.erase_window(win)
        self._render()

    def erase_line(self):
        self._sg.erase_line()
        self._render()

    def refresh(self):
        self._render()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def read_line(self, max_chars: int, time_tenths: int = 0,
                  time_routine_cb=None) -> str:
        self._render()
        buf = []
        timed = time_tenths > 0 and time_routine_cb is not None
        with _timed_input_mode(timed):
            deadline = time.monotonic() + time_tenths / 10.0 if timed else None
            while True:
                if timed:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        if time_routine_cb():
                            self._sg.print_str('\n')
                            self._render()
                            return ''
                        deadline = time.monotonic() + time_tenths / 10.0
                        continue
                    if not _key_ready(remaining):
                        continue
                ch = _getch_raw() if timed else _getch()
                if ch in ('\r', '\n'):
                    self._sg.print_str('\n')
                    self._render()
                    return ''.join(buf)
                elif ch in ('\x08', '\x7f'):   # backspace
                    if buf:
                        buf.pop()
                        sg = self._sg
                        sg._lo_col -= 1
                        if sg._lo_col < 0:
                            sg._lo_col = COLS - 1
                            sg._lo_row = max(sg._upper_rows, sg._lo_row - 1)
                        sg._put(sg._lo_row, sg._lo_col, ' ', 0)
                        self._render()
                elif ch.isprintable() and len(buf) < max_chars - 1:
                    buf.append(ch)
                    self._sg.print_str(ch)
                    self._render()

    def read_char(self, time_tenths: int = 0, time_routine_cb=None) -> str:
        self._render()
        timed = time_tenths > 0 and time_routine_cb is not None
        if not timed:
            return _getch()
        with _timed_input_mode(timed):
            deadline = time.monotonic() + time_tenths / 10.0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    if time_routine_cb():
                        return '\r'
                    deadline = time.monotonic() + time_tenths / 10.0
                    continue
                if not _key_ready(remaining):
                    continue
                return _getch_raw()

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------

    def run(self, processor):
        self._run_loop(processor)
