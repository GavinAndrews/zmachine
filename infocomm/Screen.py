import sys
import os
import shutil

if sys.platform == 'win32':
    import ctypes
    import msvcrt
else:
    import tty
    import termios
    import select


# Z-Machine color codes -> ANSI color index (0-7)
_ZM_COLOR_TO_ANSI = {
    2: 0,   # black
    3: 1,   # red
    4: 2,   # green
    5: 3,   # yellow
    6: 4,   # blue
    7: 5,   # magenta
    8: 6,   # cyan
    9: 7,   # white
}

# Z-Machine text style bits
STYLE_REVERSE  = 1
STYLE_BOLD     = 2
STYLE_EMPHASIS = 4   # underline
STYLE_FIXED    = 8


def _write(s):
    sys.stdout.write(s)


def _flush():
    sys.stdout.flush()


class Screen:
    def __init__(self):
        self.total_rows = 25
        self.total_cols = 80
        self.upper_rows = 0        # height of upper window (0 = unsplit)
        self.current_win = 0       # 0 = lower, 1 = upper
        self.upper_row = 1         # cursor row within upper window (1-based)
        self.upper_col = 1         # cursor col within upper window (1-based)
        self.style = 0
        self.fg = -1               # -1 = default
        self.bg = -1
        self.transcript_file = None
        self.stream2_active = False
        self.ansi = sys.stdout.isatty()   # False in PyCharm Run / piped output

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def init(self):
        if self.ansi:
            self._enable_ansi_windows()
        size = shutil.get_terminal_size(fallback=(80, 25))
        self.total_cols = size.columns
        self.total_rows = size.lines
        if self.ansi:
            _write('\x1b[?1049h')   # enter alternate screen buffer
            _write('\x1b[2J')       # clear screen
            _write('\x1b[H')        # cursor to top-left
            _flush()
        if sys.platform != 'win32' and sys.stdin.isatty():
            import termios as _t
            self._cooked_attrs = _t.tcgetattr(sys.stdin.fileno())

    def reset(self):
        if self.ansi:
            self._reset_style()
            _write('\x1b[?1049l')   # leave alternate screen buffer
            _flush()
        if self.transcript_file:
            self.transcript_file.close()
            self.transcript_file = None

    def get_size(self):
        return (self.total_rows, self.total_cols)

    # ------------------------------------------------------------------ #
    # Window management                                                    #
    # ------------------------------------------------------------------ #

    def split_window(self, height):
        if not self.ansi:
            self.upper_rows = height
            return
        if height == 0:
            self.upper_rows = 0
            _write('\x1b[r')    # reset scroll region to full screen
        else:
            self.upper_rows = height
            top = height + 1
            bot = self.total_rows
            _write(f'\x1b[{top};{bot}r')
            self._erase_region(1, 1, height, self.total_cols)
        _flush()

    def set_window(self, win):
        if win == self.current_win:
            return
        self.current_win = win
        if not self.ansi:
            return
        if win == 1:
            _write('\x1b[s')                                    # save lower-window cursor
            _write(f'\x1b[{self.upper_row};{self.upper_col}H') # go to upper-window cursor
        else:
            _write('\x1b[u')                                    # restore lower-window cursor
        _flush()

    def erase_window(self, win):
        if not self.ansi:
            if win in (-1, 0):
                _write('\n' * 3)
                _flush()
            return
        if win == -1:
            _write('\x1b[r')
            _write('\x1b[2J')
            _write('\x1b[H')
            self.upper_rows = 0
        elif win == 1 and self.upper_rows > 0:
            self._erase_region(1, 1, self.upper_rows, self.total_cols)
        elif win == 0:
            top = self.upper_rows + 1
            self._erase_region(top, 1, self.total_rows, self.total_cols)
        _flush()

    def erase_line(self):
        if not self.ansi:
            return
        _write('\x1b[K')
        _flush()

    def set_cursor(self, row, col):
        if not self.ansi:
            self.upper_row = row
            self.upper_col = col
            return
        if self.current_win == 1:
            row = max(1, min(row, self.upper_rows))
            col = max(1, min(col, self.total_cols))
            self.upper_row = row
            self.upper_col = col
            _write(f'\x1b[{row};{col}H')
            _flush()

    def get_cursor(self):
        if self.current_win == 1:
            return (self.upper_row, self.upper_col)
        # Lower window: return a plausible position; we don't track it exactly
        return (self.upper_rows + 1, 1)

    # ------------------------------------------------------------------ #
    # Text style / colour                                                  #
    # ------------------------------------------------------------------ #

    def set_text_style(self, style):
        self.style = style
        if self.ansi:
            self._apply_style()

    def set_colour(self, fg, bg):
        self.fg = fg
        self.bg = bg
        if self.ansi:
            self._apply_style()

    # ------------------------------------------------------------------ #
    # Text output                                                          #
    # ------------------------------------------------------------------ #

    def print_char(self, ch):
        _write(ch)
        if self.current_win == 1:
            # Track cursor movement in upper window
            if ch == '\n':
                self.upper_row += 1
                self.upper_col = 1
            else:
                self.upper_col += 1
        if self.stream2_active and self.transcript_file:
            self.transcript_file.write(ch)

    def print_str(self, s):
        _write(s)
        if self.current_win == 1:
            for ch in s:
                if ch == '\n':
                    self.upper_row += 1
                    self.upper_col = 1
                else:
                    self.upper_col += 1
        if self.stream2_active and self.transcript_file:
            self.transcript_file.write(s)

    def new_line(self):
        self.print_char('\n')

    def print_location_prompt(self, loc_text):
        """Print location line + '> ' before game input; write clean text to transcript."""
        if self.ansi:
            _write(f'\r\x1b[K{loc_text}\n> ')
        else:
            _write(f'\n{loc_text}\n> ')
        _flush()
        if self.stream2_active and self.transcript_file:
            self.transcript_file.write(f'{loc_text}\n> ')

    def refresh(self):
        _flush()

    # ------------------------------------------------------------------ #
    # Input                                                                #
    # ------------------------------------------------------------------ #

    def read_line(self, max_chars, time_tenths=0, time_routine_cb=None):
        import time as time_mod
        self.refresh()

        if time_tenths == 0 or time_routine_cb is None:
            line = self._readline_plain(max_chars)
        else:
            line = self._readline_timed(max_chars, time_tenths, time_routine_cb, time_mod)

        if self.stream2_active and self.transcript_file:
            self.transcript_file.write(line + '\n')
        return line

    def read_char(self, time_tenths=0, time_routine_cb=None):
        import time as time_mod
        self.refresh()

        if time_tenths == 0 or time_routine_cb is None:
            ch = self._read_single_char_plain()
        else:
            ch = self._read_single_char_timed(time_tenths, time_routine_cb, time_mod)
        return ch

    # ------------------------------------------------------------------ #
    # Transcript (stream 2)                                                #
    # ------------------------------------------------------------------ #

    def open_transcript(self, path=None):
        if self.transcript_file:
            return  # already open
        if path is None:
            path = 'transcript.txt'
        self.transcript_file = open(path, 'a', encoding='utf-8')
        self.stream2_active = True

    def close_transcript(self):
        self.stream2_active = False
        if self.transcript_file:
            self.transcript_file.flush()
            self.transcript_file.close()
            self.transcript_file = None

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _enable_ansi_windows(self):
        if sys.platform != 'win32':
            return
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        ENABLE_PROCESSED_OUTPUT = 0x0001
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong(0)
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value
                                | ENABLE_VIRTUAL_TERMINAL_PROCESSING
                                | ENABLE_PROCESSED_OUTPUT)

    def _apply_style(self):
        codes = ['0']  # always reset first
        if self.style & STYLE_REVERSE:
            codes.append('7')
        if self.style & STYLE_BOLD:
            codes.append('1')
        if self.style & STYLE_EMPHASIS:
            codes.append('4')
        if self.fg in _ZM_COLOR_TO_ANSI:
            codes.append(str(30 + _ZM_COLOR_TO_ANSI[self.fg]))
        elif self.fg == 1:
            codes.append('39')   # default fg
        if self.bg in _ZM_COLOR_TO_ANSI:
            codes.append(str(40 + _ZM_COLOR_TO_ANSI[self.bg]))
        elif self.bg == 1:
            codes.append('49')   # default bg
        _write(f'\x1b[{";".join(codes)}m')

    def _reset_style(self):
        _write('\x1b[0m')

    def _erase_region(self, top, left, bottom, right):
        for row in range(top, bottom + 1):
            _write(f'\x1b[{row};{left}H')
            _write('\x1b[K')

    # ------------------------------------------------------------------ #
    # Low-level input                                                      #
    # ------------------------------------------------------------------ #

    def _readline_plain(self, max_chars):
        if not sys.stdin.isatty():
            line = sys.stdin.readline()
            return line.rstrip('\n\r')[:max_chars - 1]

        # Restore cooked mode on Linux (may have been left raw by a read_char).
        if sys.platform != 'win32' and hasattr(self, '_cooked_attrs'):
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._cooked_attrs)

        # input() gives full native line editing (backspace, Delete, Home, End,
        # arrows) on both Windows and Linux without us reimplementing any of it.
        try:
            line = input()
        except EOFError:
            line = ''
        return line[:max_chars - 1]

    def _erase_back(self):
        """Erase the character behind the cursor (works in timed raw-input loops)."""
        if self.ansi:
            _write('\b\x1b[K')   # move left, erase to end of line
        else:
            _write('\b \b')      # fallback: overwrite with space

    def _readline_timed(self, max_chars, time_tenths, time_routine_cb, time_mod):
        interval = time_tenths / 10.0
        last_tick = time_mod.time()
        line = []

        if sys.platform == 'win32':
            while True:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()   # no auto-echo; we echo manually
                    if ch in ('\r', '\n'):
                        _write('\n')
                        _flush()
                        return ''.join(line)
                    elif ch in ('\x00', '\xe0'):
                        msvcrt.getwch()    # consume second byte of extended key
                    elif ch in ('\x08', '\x7f'):
                        if line:
                            line.pop()
                            self._erase_back()
                            _flush()
                    elif ch == '\x03':
                        raise KeyboardInterrupt
                    elif len(line) < max_chars - 1 and ch >= ' ':
                        _write(ch)
                        _flush()
                        line.append(ch)
                else:
                    now = time_mod.time()
                    if now - last_tick >= interval:
                        last_tick = now
                        if time_routine_cb():
                            _write('\n')
                            _flush()
                            return ''.join(line)
                    time_mod.sleep(0.02)
        else:
            fd = sys.stdin.fileno()
            tty.setraw(fd)
            try:
                while True:
                    ready = select.select([sys.stdin], [], [], 0.02)[0]
                    if ready:
                        ch = sys.stdin.read(1)
                        if ch in ('\r', '\n'):
                            _write('\n')
                            _flush()
                            return ''.join(line)
                        elif ch in ('\x08', '\x7f'):
                            if line:
                                line.pop()
                                self._erase_back()
                                _flush()
                        elif ch == '\x03':
                            raise KeyboardInterrupt
                        elif len(line) < max_chars - 1 and ch >= ' ':
                            _write(ch)
                            _flush()
                            line.append(ch)
                    else:
                        now = time_mod.time()
                        if now - last_tick >= interval:
                            last_tick = now
                            if time_routine_cb():
                                _write('\n')
                                _flush()
                                return ''.join(line)
            finally:
                if hasattr(self, '_cooked_attrs'):
                    termios.tcsetattr(fd, termios.TCSADRAIN, self._cooked_attrs)

    def _read_single_char_plain(self):
        if not sys.stdin.isatty():
            ch = sys.stdin.read(1)
            return ch if ch else '\r'
        if sys.platform == 'win32':
            return msvcrt.getwch()
        else:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            tty.setraw(fd)
            try:
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            return ch

    def _read_single_char_timed(self, time_tenths, time_routine_cb, time_mod):
        interval = time_tenths / 10.0
        last_tick = time_mod.time()

        if sys.platform == 'win32':
            while True:
                if msvcrt.kbhit():
                    return msvcrt.getwch()
                now = time_mod.time()
                if now - last_tick >= interval:
                    last_tick = now
                    if time_routine_cb():
                        return '\r'
                time_mod.sleep(0.02)
        else:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            tty.setraw(fd)
            try:
                while True:
                    ready = select.select([sys.stdin], [], [], 0.02)[0]
                    if ready:
                        return sys.stdin.read(1)
                    now = time_mod.time()
                    if now - last_tick >= interval:
                        last_tick = now
                        if time_routine_cb():
                            return '\r'
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
