"""
ScreenGrid.py — Shared 25×80 terminal character grid.

Contains all Z-machine window logic (split, scroll, cursor) with no rendering
or I/O dependencies.  Used by the ANSI, curses, and Qt backends.
"""

ROWS = 25
COLS = 80

STYLE_REVERSE  = 1
STYLE_BOLD     = 2
STYLE_EMPHASIS = 4   # underline
STYLE_FIXED    = 8


class Cell:
    __slots__ = ('char', 'style')

    def __init__(self):
        self.char  = ' '
        self.style = 0

    def reset(self):
        self.char  = ' '
        self.style = 0

    def copy_from(self, other):
        self.char  = other.char
        self.style = other.style


class ScreenGrid:
    """Mutable 25×80 grid with Z-machine upper/lower window semantics."""

    def __init__(self):
        self._grid         = [[Cell() for _ in range(COLS)] for _ in range(ROWS)]
        self._upper_rows   = 0
        self._current_win  = 0
        self._current_style = 0
        self._up_row = 0
        self._up_col = 0
        self._lo_row = 0
        self._lo_col = 0
        self.scroll_count  = 0   # lower-window scrolls since last input reset

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clear_rows(self, r0, r1):
        for r in range(max(0, r0), min(ROWS, r1 + 1)):
            for c in range(COLS):
                self._grid[r][c].reset()

    def _scroll_lower(self):
        top = self._upper_rows
        for r in range(top, ROWS - 1):
            for c in range(COLS):
                self._grid[r][c].copy_from(self._grid[r + 1][c])
        for c in range(COLS):
            self._grid[ROWS - 1][c].reset()
        self.scroll_count += 1

    def reset_scroll_count(self):
        self.scroll_count = 0

    def _put(self, r, c, ch, style):
        if 0 <= r < ROWS and 0 <= c < COLS:
            self._grid[r][c].char  = ch
            self._grid[r][c].style = style

    # ------------------------------------------------------------------
    # Z-machine window operations
    # ------------------------------------------------------------------

    def split_window(self, height):
        old = self._upper_rows
        self._upper_rows = height
        if height > old:
            self._clear_rows(old, height - 1)
        if self._lo_row < height:
            self._lo_row = height
            self._lo_col = 0

    def set_window(self, win):
        self._current_win = win

    def set_cursor(self, row, col):
        if self._current_win == 1:
            self._up_row = max(0, min(row - 1, max(0, self._upper_rows - 1)))
            self._up_col = max(0, min(col - 1, COLS - 1))

    def get_cursor(self):
        if self._current_win == 1:
            return (self._up_row + 1, self._up_col + 1)
        return (self._lo_row + 1, self._lo_col + 1)

    def set_text_style(self, style):
        self._current_style = style

    def erase_window(self, win):
        if win == -1:
            self._clear_rows(0, ROWS - 1)
            self._upper_rows  = 0
            self._current_win = 0
            self._lo_row = 0
            self._lo_col = 0
        elif win == 0:
            self._clear_rows(self._upper_rows, ROWS - 1)
            self._lo_row = self._upper_rows
            self._lo_col = 0
        elif win == 1 and self._upper_rows > 0:
            self._clear_rows(0, self._upper_rows - 1)
            self._up_row = 0
            self._up_col = 0

    def erase_line(self):
        if self._current_win == 1:
            r, c = self._up_row, self._up_col
        else:
            r, c = self._lo_row, self._lo_col
        for col in range(c, COLS):
            self._grid[r][col].reset()

    def print_str(self, s):
        if self._current_win == 1:
            self._write_upper(s)
        else:
            self._write_lower(s)

    def _write_upper(self, s):
        style = self._current_style
        top   = self._upper_rows
        for ch in s:
            if ch == '\n':
                self._up_col  = 0
                self._up_row += 1
                if self._up_row >= top:
                    self._up_row = top - 1
            else:
                self._put(self._up_row, self._up_col, ch, style)
                self._up_col += 1
                if self._up_col >= COLS:
                    self._up_col  = 0
                    self._up_row += 1
                    if self._up_row >= top:
                        self._up_row = top - 1

    def _write_lower(self, s):
        style = self._current_style
        for ch in s:
            if ch == '\n':
                self._lo_col  = 0
                self._lo_row += 1
                if self._lo_row >= ROWS:
                    self._scroll_lower()
                    self._lo_row = ROWS - 1
            else:
                self._put(self._lo_row, self._lo_col, ch, style)
                self._lo_col += 1
                if self._lo_col >= COLS:
                    self._lo_col  = 0
                    self._lo_row += 1
                    if self._lo_row >= ROWS:
                        self._scroll_lower()
                        self._lo_row = ROWS - 1
