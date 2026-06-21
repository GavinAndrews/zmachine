"""
ScreenCurses.py — Python curses backend.

Uses a ScreenGrid for all Z-machine window logic, then renders the full grid
to curses stdscr after each change.  This gives identical cell-persistence
behaviour to the Qt backend (poem rows remain until scrolled over).

Requires: curses (stdlib on Linux/macOS; 'pip install windows-curses' on Windows)
"""

import sys
from ScreenBase import ScreenBase
from ScreenGrid import ScreenGrid, ROWS, COLS, STYLE_REVERSE, STYLE_BOLD, STYLE_EMPHASIS

# curses is imported lazily inside run() so that importing this module
# doesn't fail when --ui qt/plain/ansi is selected.


class CursesScreen(ScreenBase):

    def __init__(self):
        super().__init__()
        self._sg  = ScreenGrid()
        self._scr = None   # set inside curses.wrapper

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init(self):
        pass   # real init happens inside curses.wrapper in run()

    def reset(self):
        if self.transcript_file:
            self.close_transcript()
        if self._scr is not None:
            curses.endwin()
            self._scr = None

    def _curses_setup(self, stdscr):
        import curses as _c
        self._scr = stdscr
        _c.noecho()
        _c.cbreak()
        stdscr.keypad(True)
        _c.curs_set(1)
        if _c.has_colors():
            _c.start_color()
            _c.use_default_colors()
        stdscr.clear()
        stdscr.refresh()

    # ------------------------------------------------------------------
    # Rendering — full repaint after every grid change
    # ------------------------------------------------------------------

    def _render(self):
        if self._scr is None:
            return
        import curses as _c
        sg  = self._sg
        scr = self._scr
        for r in range(ROWS):
            for c in range(COLS):
                cell = sg._grid[r][c]
                attr = _c.A_NORMAL
                if cell.style & STYLE_REVERSE:  attr |= _c.A_REVERSE
                if cell.style & STYLE_BOLD:     attr |= _c.A_BOLD
                if cell.style & STYLE_EMPHASIS: attr |= _c.A_UNDERLINE
                try:
                    scr.addch(r, c, cell.char, attr)
                except _c.error:
                    pass   # bottom-right corner raises on some terminals
        try:
            scr.move(sg._lo_row, sg._lo_col)
        except _c.error:
            pass
        scr.refresh()

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
        import curses as _c
        self._render()
        buf = []
        while True:
            ch = self._scr.getch()
            if ch in (_c.KEY_ENTER, ord('\n'), ord('\r')):
                self._sg.print_str('\n')
                self._render()
                return ''.join(buf)
            elif ch in (_c.KEY_BACKSPACE, ord('\x08'), ord('\x7f'), 127):
                if buf:
                    buf.pop()
                    sg = self._sg
                    sg._lo_col -= 1
                    if sg._lo_col < 0:
                        sg._lo_col = COLS - 1
                        sg._lo_row = max(sg._upper_rows, sg._lo_row - 1)
                    sg._put(sg._lo_row, sg._lo_col, ' ', 0)
                    self._render()
            elif 32 <= ch <= 126 and len(buf) < max_chars - 1:
                self._sg.print_str(chr(ch))
                buf.append(chr(ch))
                self._render()

    def read_char(self, time_tenths: int = 0, time_routine_cb=None) -> str:
        import curses as _c
        self._render()
        ch = self._scr.getch()
        _MAP = {
            _c.KEY_UP:        '\x1b[A',
            _c.KEY_DOWN:      '\x1b[B',
            _c.KEY_RIGHT:     '\x1b[C',
            _c.KEY_LEFT:      '\x1b[D',
            _c.KEY_BACKSPACE: '\x08',
            _c.KEY_ENTER:     '\r',
            ord('\n'):        '\r',
            ord('\r'):        '\r',
            ord('\x1b'):      '\x1b',
        }
        if ch in _MAP:
            return _MAP[ch]
        if 32 <= ch <= 126:
            return chr(ch)
        return '\r'

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------

    def run(self, processor):
        import curses as _c

        def _main(stdscr):
            self._curses_setup(stdscr)
            self._run_loop(processor)

        try:
            _c.wrapper(_main)
        except _c.error as e:
            sys.exit(f"curses error: {e}")
