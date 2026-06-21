"""
ScreenAnsi.py — ANSI escape-code terminal backend.

Uses the alternate screen buffer so the game display doesn't mix with the
shell's scrollback.  The full 25×80 grid is repainted after every write,
which keeps the implementation simple and the display always correct.

Works in any ANSI-capable terminal: Windows Terminal, VSCode, xterm, etc.
Does NOT work in bare Windows Command Prompt (cmd.exe without VT enabled).
"""

import sys
from ScreenBase import ScreenBase
from ScreenGrid import ScreenGrid, ROWS, COLS, STYLE_REVERSE, STYLE_BOLD, STYLE_EMPHASIS


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

    def __init__(self):
        super().__init__()
        self._sg = ScreenGrid()

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
        out = [_HIDE]
        cur_style = -1
        for r in range(ROWS):
            out.append(_pos(r + 1, 1))
            for c in range(COLS):
                cell = sg._grid[r][c]
                if cell.style != cur_style:
                    cur_style = cell.style
                    out.append(_style(cur_style))
                out.append(cell.char)
        out.append(_RESET)
        # Place terminal cursor at lower-window input position
        out.append(_pos(sg._lo_row + 1, sg._lo_col + 1))
        out.append(_SHOW)
        sys.stdout.write(''.join(out))
        sys.stdout.flush()

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
        while True:
            ch = _getch()
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
        return _getch()

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------

    def run(self, processor):
        self._run_loop(processor)
