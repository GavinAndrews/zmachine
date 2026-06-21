"""Headless (no-Qt) screen for automated testing.

All output is captured as a list of ScreenEvents.  Input comes exclusively
from the Scripting object passed to the Processor; if scripting is exhausted
and read_line/read_char is called directly, StopExecution is raised to end
the run loop cleanly.
"""


class StopExecution(Exception):
    """Raised when the scripting queue is exhausted and the game asks for input."""


class ScreenEvent:
    __slots__ = ('type', 'kwargs')

    def __init__(self, type_, **kwargs):
        self.type   = type_
        self.kwargs = kwargs

    def __repr__(self):
        kv = ', '.join(f'{k}={v!r}' for k, v in self.kwargs.items())
        return f'{self.type}({kv})'


class HeadlessScreen:
    """Drop-in replacement for ZMachineScreen that records every screen event.

    Lifecycle:
      screen = HeadlessScreen()
      screen.init()
      processor = build_machine(game_path, screen, scripting=ListScripting([...]))
      # drive processor in a loop until StopExecution
      # then inspect screen.events / screen.upper_text() / screen.lower_text()
    """

    def __init__(self):
        self.events        = []
        self.current_win   = 0
        self.upper_rows    = 0
        self.current_style = 0
        self.current_fg    = -1
        self.current_bg    = -1
        self.stream2_active   = False
        self.transcript_file  = None
        self.processor        = None
        self._upper_cur_row   = 1
        self._upper_cur_col   = 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evt(self, type_, **kwargs):
        e = ScreenEvent(type_, **kwargs)
        self.events.append(e)
        return e

    # ------------------------------------------------------------------
    # Screen API — output
    # ------------------------------------------------------------------

    def init(self):
        pass

    def append_text(self, text, **_kwargs):
        # Called by Infocomm.py for the welcome banner; treat as lower-window print.
        self._evt('print', win=0, text=text, style=0)

    def print_str(self, s):
        win = 1 if (self.current_win == 1 and self.upper_rows > 0) else 0
        self._evt('print', win=win, text=s, style=self.current_style)

    def print_char(self, ch):
        self.print_str(ch)

    def new_line(self):
        self.print_str('\n')

    # ------------------------------------------------------------------
    # Screen API — window management
    # ------------------------------------------------------------------

    def split_window(self, height):
        old_rows = self.upper_rows
        self.upper_rows = height
        if old_rows > 1 and height <= 1:
            # Deferred in the GUI (collapses on Enter); record the intent separately
            # so the test can see the popup lifecycle clearly.
            self._evt('split_window_deferred', height=height)
        else:
            self._evt('split_window', height=height)

    def erase_window(self, win):
        self._evt('erase_window', win=win)
        if win == -1:
            self.upper_rows  = 0
            self.current_win = 0

    def read_line(self, max_chars=80, time_tenths=0, time_routine_cb=None):
        raise StopExecution('scripting exhausted at read_line')

    def read_char(self, time_tenths=0, time_routine_cb=None):
        raise StopExecution('scripting exhausted at read_char')

    def set_window(self, win):
        self.current_win = win
        self._evt('set_window', win=win)

    def set_cursor(self, row, col):
        self._upper_cur_row = row
        self._upper_cur_col = col
        self._evt('set_cursor', row=row, col=col)

    def get_cursor(self):
        if self.current_win == 1:
            return (self._upper_cur_row, self._upper_cur_col)
        return (1, 1)

    def erase_line(self):
        self._evt('erase_line')

    def set_text_style(self, style):
        self.current_style = style
        self._evt('set_text_style', style=style)

    def set_colour(self, fg, bg):
        self.current_fg = fg
        self.current_bg = bg

    def update_status_line(self, location, score, turns):
        self._evt('status', location=location, score=score, turns=turns)

    def print_location_prompt(self, loc_text):
        self._evt('location_prompt', text=loc_text)

    def refresh(self):
        pass

    # ------------------------------------------------------------------
    # Screen API — misc
    # ------------------------------------------------------------------

    def get_size(self):
        return (25, 80)

    def open_transcript(self, path=None):
        pass

    def close_transcript(self):
        pass

    def reset(self):
        pass

    def exec(self):
        pass

    # ------------------------------------------------------------------
    # Analysis helpers
    # ------------------------------------------------------------------

    def lower_text(self):
        """All text written to the lower window (window 0), concatenated."""
        return ''.join(e.kwargs['text'] for e in self.events
                       if e.type == 'print' and e.kwargs['win'] == 0)

    def upper_text(self):
        """All text written to the upper window (window 1), concatenated."""
        return ''.join(e.kwargs['text'] for e in self.events
                       if e.type == 'print' and e.kwargs['win'] == 1)

    def popup_events(self):
        """Events from the last *significant* split_window (height > 1) through its close.

        A popup is considered closed by either:
          - erase_window(-1)  — explicit full-screen clear
          - split_window(h<=1) — game reducing upper window back to status-bar height

        Height-1 splits are the 1-row status bar, not real popups, so they are excluded
        from being treated as a popup open.
        """
        last_sig = None
        for i, e in enumerate(self.events):
            if e.type == 'split_window' and e.kwargs['height'] > 1:
                last_sig = i   # keep updating — we want the LAST significant split

        if last_sig is None:
            return []

        for i in range(last_sig + 1, len(self.events)):
            e = self.events[i]
            closed = (
                (e.type == 'erase_window' and e.kwargs['win'] == -1) or
                (e.type == 'split_window' and e.kwargs['height'] <= 1) or
                e.type == 'split_window_deferred'
            )
            if closed:
                return self.events[last_sig : i + 1]

        return self.events[last_sig:]   # popup opened but not yet closed

    def format_summary(self, max_text=80):
        """Human-readable one-line-per-event summary."""
        lines = []
        for e in self.events:
            if e.type == 'print':
                text = repr(e.kwargs['text'])
                if len(text) > max_text:
                    text = text[:max_text - 4] + "...'"
                lines.append(f"  [W{e.kwargs['win']}] {text}")
            else:
                lines.append(f"  [{e.type.upper()}] {e.kwargs}")
        return '\n'.join(lines)
