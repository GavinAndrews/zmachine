"""
Screen.py — unified terminal-grid display for the Z-Machine interpreter.

The entire 25×80 character grid is one surface, exactly like a real terminal.
The upper and lower Z-machine windows are logical regions of that grid:

    rows 0 .. upper_rows-1   →  upper window  (fixed, no scroll)
    rows upper_rows .. 24    →  lower window  (scrolling)

When split_window collapses from 14 rows back to 1, the poem character cells
in rows 1-13 are NOT erased — they stay on screen exactly as a real terminal
would leave them.  The lower window's next output goes to the bottom of the
lower area and scrolls up from there, eventually pushing the poem off.
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QScrollArea,
    QVBoxLayout, QHBoxLayout, QTextEdit, QListWidget,
    QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
    QPushButton, QFileDialog, QLabel,
)
from PySide6.QtCore  import Qt, QTimer, QThread, QObject, QEvent
from PySide6.QtGui   import QFont, QFontMetrics, QPainter, QColor, QPen

# Z-Machine text style bits
STYLE_REVERSE  = 1
STYLE_BOLD     = 2
STYLE_EMPHASIS = 4   # underline
STYLE_FIXED    = 8

ROWS = 25
COLS = 80


# ---------------------------------------------------------------------------
# Terminal cell
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Terminal widget — the entire screen in one QPainter surface
# ---------------------------------------------------------------------------

class TerminalWidget(QWidget):
    """25×80 character-cell terminal.  Upper and lower Z-machine windows are
    regions of the same grid; no separate widgets, no separate scroll areas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._font = QFont("Courier New", 11)
        fm = QFontMetrics(self._font)
        self._cw = fm.horizontalAdvance('X')   # cell width  (monospace — all equal)
        self._ch = fm.height()                  # cell height
        self.setFixedSize(COLS * self._cw, ROWS * self._ch)
        self.setStyleSheet("background: black;")

        # The grid
        self._grid = [[Cell() for _ in range(COLS)] for _ in range(ROWS)]

        # Z-machine window state
        self._upper_rows   = 0   # rows assigned to upper window (0 = none)
        self._current_win  = 0   # 0 = lower, 1 = upper
        self._current_style = 0

        # Upper window cursor (0-indexed)
        self._up_row = 0
        self._up_col = 0

        # Lower window cursor (0-indexed)
        self._lo_row = 0
        self._lo_col = 0

        # Line-input state
        self._input_mode   = False
        self._input_buffer = ""
        self._input_max    = COLS
        self._input_row    = 0
        self._input_col    = 0

        # Single-char input state
        self._char_mode = False

        # Callbacks set by ZMachineScreen
        self.on_line_entered = None
        self.on_char_entered = None

        # Blinking cursor
        self._cursor_phase = True
        self._blink = QTimer(self)
        self._blink.timeout.connect(self._tick)
        self._blink.start(500)

    def _tick(self):
        if self._input_mode or self._char_mode:
            self._cursor_phase = not self._cursor_phase
            self.update()

    # ------------------------------------------------------------------
    # Internal grid helpers
    # ------------------------------------------------------------------

    def _clear_rows(self, r0, r1):
        for r in range(max(0, r0), min(ROWS, r1 + 1)):
            for c in range(COLS):
                self._grid[r][c].reset()

    def _scroll_lower(self):
        """Scroll the lower-window area up by one line."""
        top = self._upper_rows
        for r in range(top, ROWS - 1):
            for c in range(COLS):
                self._grid[r][c].copy_from(self._grid[r + 1][c])
        for c in range(COLS):
            self._grid[ROWS - 1][c].reset()

    def _put(self, r, c, ch, style):
        if 0 <= r < ROWS and 0 <= c < COLS:
            self._grid[r][c].char  = ch
            self._grid[r][c].style = style

    # ------------------------------------------------------------------
    # Z-machine screen operations
    # ------------------------------------------------------------------

    def split_window(self, height):
        old = self._upper_rows
        self._upper_rows = height
        # V4: split_window does NOT clear the upper window (spec §8.7.2.1)
        # Only clear newly added rows (growing the upper window)
        if height > old:
            self._clear_rows(old, height - 1)
        # Lower cursor must stay inside the lower area
        if self._lo_row < height:
            self._lo_row = height
            self._lo_col = 0
        self.update()

    def set_window(self, win):
        self._current_win = win

    def set_cursor(self, row, col):
        """Z-machine set_cursor (1-indexed).  Active for the current window."""
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
        self.update()

    def erase_line(self):
        if self._current_win == 1:
            r, c = self._up_row, self._up_col
        else:
            r, c = self._lo_row, self._lo_col
        for col in range(c, COLS):
            self._grid[r][col].reset()
        self.update()

    def print_str(self, s):
        if self._current_win == 1:
            self._write_upper(s)
        else:
            self._write_lower(s)
        self.update()

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

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def start_line_input(self, max_chars=COLS):
        self._input_mode   = True
        self._input_buffer = ""
        self._input_max    = max_chars
        self._input_row    = self._lo_row
        self._input_col    = self._lo_col
        self._cursor_phase = True
        self.setFocus()
        self.update()

    def start_char_input(self):
        self._char_mode    = True
        self._cursor_phase = True
        self.setFocus()
        self.update()

    def keyPressEvent(self, event):
        if self._input_mode:
            self._key_line(event)
        elif self._char_mode:
            self._key_char(event)
        else:
            super().keyPressEvent(event)

    def _key_line(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            text = self._input_buffer
            self._input_buffer = ""
            self._input_mode   = False
            self._write_lower('\n')
            self.update()
            if self.on_line_entered:
                self.on_line_entered(text)
        elif key == Qt.Key.Key_Backspace:
            if self._input_buffer:
                self._input_buffer = self._input_buffer[:-1]
                # Erase the last echoed character
                self._lo_col -= 1
                if self._lo_col < 0:
                    self._lo_col = COLS - 1
                    self._lo_row = max(self._upper_rows, self._lo_row - 1)
                self._put(self._lo_row, self._lo_col, ' ', 0)
                self.update()
        else:
            ch = event.text()
            if ch and ch.isprintable() and len(self._input_buffer) < self._input_max - 1:
                self._input_buffer += ch
                self._write_lower(ch)
                self.update()

    def _key_char(self, event):
        self._char_mode = False
        key  = event.key()
        text = event.text()
        if text and text.isprintable():
            result = text
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            result = '\r'
        elif key == Qt.Key.Key_Escape:
            result = '\x1b'
        elif key == Qt.Key.Key_Backspace:
            result = '\x08'
        elif key == Qt.Key.Key_Delete:
            result = '\x7f'
        elif key == Qt.Key.Key_Up:
            result = '\x1b[A'
        elif key == Qt.Key.Key_Down:
            result = '\x1b[B'
        elif key == Qt.Key.Key_Right:
            result = '\x1b[C'
        elif key == Qt.Key.Key_Left:
            result = '\x1b[D'
        else:
            result = '\r'
        self.update()
        if self.on_char_entered:
            self.on_char_entered(result)

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setFont(self._font)
        fm     = QFontMetrics(self._font)
        ascent = fm.ascent()
        cw, ch = self._cw, self._ch

        BLACK = QColor(0, 0, 0)
        WHITE = QColor(204, 204, 204)
        BRITE = QColor(255, 255, 255)

        for r in range(ROWS):
            for c in range(COLS):
                cell = self._grid[r][c]
                x = c * cw
                y = r * ch

                if cell.style & STYLE_REVERSE:
                    bg, fg = WHITE, BLACK
                else:
                    bg, fg = BLACK, WHITE

                painter.fillRect(x, y, cw, ch, bg)

                char = cell.char
                if char != ' ':
                    painter.setPen(fg)
                    painter.drawText(x, y + ascent, char)

        # Block cursor at lower cursor position when accepting input
        if (self._input_mode or self._char_mode) and self._cursor_phase:
            r, c = self._lo_row, self._lo_col
            x = c * cw
            y = r * ch
            painter.fillRect(x, y, cw, ch, BRITE)
            char = self._grid[r][c].char
            if char != ' ':
                painter.setPen(BLACK)
                painter.drawText(x, y + ascent, char)

        painter.end()


# ---------------------------------------------------------------------------
# Debug / inspector windows (unchanged from previous version)
# ---------------------------------------------------------------------------

class DebugWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Z-Machine Debug Log")
        self.setGeometry(100, 100, 600, 400)
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(lambda: self.text_area.clear())
        pause_btn = QPushButton("Pause")
        pause_btn.setCheckable(True)
        pause_btn.clicked.connect(self._toggle_pause)
        toolbar.addWidget(clear_btn)
        toolbar.addWidget(pause_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.text_area = QTextEdit()
        self.text_area.setFont(QFont("Courier New", 9))
        self.text_area.setReadOnly(True)
        layout.addWidget(self.text_area)
        self.paused = False

    def _toggle_pause(self, checked):
        self.paused = checked

    def append(self, text, color='white'):
        if self.paused:
            return
        self.text_area.setTextColor(QColor(color))
        self.text_area.append(text)
        self.text_area.ensureCursorVisible()


class ObjectWindow(QWidget):
    def __init__(self, processor=None, parent=None):
        super().__init__(parent)
        self.processor = processor
        self.setWindowTitle("Object State")
        self.setGeometry(100, 100, 500, 400)
        layout = QVBoxLayout(self)
        btn = QPushButton("Refresh")
        btn.clicked.connect(self.refresh)
        layout.addWidget(btn)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Object", "Parent", "Child", "Sibling"])
        layout.addWidget(self.tree)

    def refresh(self):
        self.tree.clear()
        if not self.processor:
            return
        obj_count = self.processor.object_table.object_count
        for i in range(1, obj_count + 1):
            try:
                obj = self.processor.object_table.get_object_table_entry(i)
                if obj is None:
                    continue
                try:
                    name = obj.get_property_table().get_description().strip()
                except Exception:
                    name = f"Obj#{i}"
                item = QTreeWidgetItem([
                    name,
                    str(obj.get_parent_object_number()),
                    str(obj.get_child_object_number()),
                    str(obj.get_next_sibling_object_number()),
                ])
                self.tree.addTopLevelItem(item)
            except Exception:
                continue


class GlobalsWindow(QWidget):
    def __init__(self, processor=None, parent=None):
        super().__init__(parent)
        self.processor = processor
        self.setWindowTitle("Global Variables")
        self.setGeometry(100, 100, 400, 300)
        layout = QVBoxLayout(self)
        btn = QPushButton("Refresh")
        btn.clicked.connect(self.refresh)
        layout.addWidget(btn)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Global", "Value"])
        layout.addWidget(self.table)

    def refresh(self):
        if not self.processor:
            return
        self.table.setRowCount(0)
        for g in range(32):
            try:
                val = self.processor.globals.read_global(g)
                self.table.insertRow(g)
                self.table.setItem(g, 0, QTableWidgetItem(f"G{g:02d}"))
                self.table.setItem(g, 1, QTableWidgetItem(f"{val:5d} (0x{val:04X})"))
            except Exception:
                pass


class StackWindow(QWidget):
    def __init__(self, processor=None, parent=None):
        super().__init__(parent)
        self.processor = processor
        self.setWindowTitle("Stack")
        self.setGeometry(100, 100, 300, 400)
        layout = QVBoxLayout(self)
        btn = QPushButton("Refresh")
        btn.clicked.connect(self.refresh)
        layout.addWidget(btn)
        self.list = QListWidget()
        layout.addWidget(self.list)

    def refresh(self):
        self.list.clear()
        if not self.processor:
            return
        stack = self.processor.stack
        for i, val in enumerate(stack.stack[:stack.sp + 1]):
            self.list.addItem(f"{i:02d}: {val:5d} (0x{val:04X})")


# ---------------------------------------------------------------------------
# ZMachineScreen — the public interface used by Instructions / Processor
# ---------------------------------------------------------------------------

class ZMachineScreen:
    def __init__(self, processor=None):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.processor      = processor
        self.main_window    = None
        self.terminal       = None
        self.debug_window   = None
        self.object_window  = None
        self.globals_window = None
        self.stack_window   = None

        self.stream2_active  = False
        self.transcript_file = None
        self.current_fg      = -1
        self.current_bg      = -1

        # Input synchronisation
        self._line_result = None
        self._char_result = None
        self._waiting     = False

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def init(self):
        self.main_window = QMainWindow()
        self.main_window.setWindowTitle("Infocomm Z-Machine Interpreter")

        menubar = self.main_window.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Open Game...", self.open_game)
        file_menu.addAction("Save Game",    self.save_game)
        file_menu.addAction("Restore Game", self.restore_game)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.main_window.close)
        view_menu = menubar.addMenu("View")
        view_menu.addAction("Debug Log", self.toggle_debug)
        view_menu.addAction("Objects",   self.toggle_objects)
        view_menu.addAction("Globals",   self.toggle_globals)
        view_menu.addAction("Stack",     self.toggle_stack)

        self.terminal = TerminalWidget()
        self.terminal.on_line_entered = self._cb_line
        self.terminal.on_char_entered = self._cb_char

        scroll = QScrollArea()
        scroll.setWidget(self.terminal)
        scroll.setWidgetResizable(False)
        scroll.setStyleSheet("QScrollArea { background: black; border: none; }")
        self.main_window.setCentralWidget(scroll)
        self.main_window.resize(
            self.terminal.width()  + 4,
            self.terminal.height() + self.main_window.menuBar().height() + 4,
        )
        self.main_window.show()

        self.debug_window   = DebugWindow()
        self.object_window  = ObjectWindow(self.processor)
        self.globals_window = GlobalsWindow(self.processor)
        self.stack_window   = StackWindow(self.processor)

        self.terminal.setFocus()

    # ------------------------------------------------------------------
    # Input callbacks
    # ------------------------------------------------------------------

    def _cb_line(self, text):
        self._line_result = text
        self._waiting     = False

    def _cb_char(self, ch):
        self._char_result = ch
        self._waiting     = False

    # ------------------------------------------------------------------
    # Screen API — output
    # ------------------------------------------------------------------

    def append_text(self, text, **_kwargs):
        """Pre-game text (welcome banner etc.) — just print to the terminal."""
        if self.terminal:
            self.terminal.print_str(text)

    def print_str(self, s):
        if self.terminal:
            self.terminal.print_str(s)
        if self.stream2_active and self.transcript_file:
            self.transcript_file.write(s)
        if self.debug_window and self.debug_window.isVisible():
            win = self.terminal._current_win if self.terminal else 0
            pc  = ''
            if self.processor and hasattr(self.processor, 'instructions'):
                pc = f"@{self.processor.instructions._current_opcode_pc:05X} "
            self.debug_window.append(f"{pc}[W{win}] {repr(s)}", color='yellow')

    def print_char(self, ch):
        self.print_str(ch)

    def new_line(self):
        self.print_str('\n')

    # ------------------------------------------------------------------
    # Screen API — window management
    # ------------------------------------------------------------------

    def split_window(self, height):
        if self.terminal:
            self.terminal.split_window(height)
        if self.debug_window:
            self.debug_window.append(f"[SPLIT_WINDOW {height}]", color='cyan')

    def set_window(self, win):
        if self.terminal:
            self.terminal.set_window(win)
        if self.debug_window:
            self.debug_window.append(f"[SET_WINDOW {win}]", color='cyan')

    def set_cursor(self, row, col):
        if self.terminal:
            self.terminal.set_cursor(row, col)

    def get_cursor(self):
        return self.terminal.get_cursor() if self.terminal else (1, 1)

    def set_text_style(self, style):
        if self.terminal:
            self.terminal.set_text_style(style)

    def set_colour(self, fg, bg):
        self.current_fg = fg
        self.current_bg = bg

    def erase_window(self, win):
        if self.terminal:
            self.terminal.erase_window(win)
        if self.debug_window:
            self.debug_window.append(f"[ERASE_WINDOW {win}]", color='cyan')

    def erase_line(self):
        if self.terminal:
            self.terminal.erase_line()

    def update_status_line(self, location, score, turns):
        pass   # V3 show_status; V4+ games draw their own status via window 1

    def print_location_prompt(self, loc_text):
        self.print_str(f'\n{loc_text}\n> ')

    def refresh(self):
        QApplication.processEvents()

    # ------------------------------------------------------------------
    # Screen API — input
    # ------------------------------------------------------------------

    def read_line(self, max_chars, time_tenths=0, time_routine_cb=None):
        self._line_result = None
        self._waiting     = True
        if self.terminal:
            self.terminal.start_line_input(max_chars)

        if time_tenths > 0 and time_routine_cb:
            def _timeout():
                if self._waiting and time_routine_cb():
                    self._line_result = ""
                    self._waiting     = False
                    if self.terminal:
                        self.terminal._input_mode = False
            QTimer.singleShot(time_tenths * 100, _timeout)

        while self._waiting:
            QApplication.processEvents()
            QThread.msleep(10)

        return self._line_result if self._line_result is not None else ""

    def read_char(self, time_tenths=0, time_routine_cb=None):
        self._char_result = None
        self._waiting     = True
        if self.terminal:
            self.terminal.start_char_input()

        if time_tenths > 0 and time_routine_cb:
            def _timeout():
                if self._waiting and time_routine_cb():
                    self._char_result = '\r'
                    self._waiting     = False
                    if self.terminal:
                        self.terminal._char_mode = False
            QTimer.singleShot(time_tenths * 100, _timeout)

        while self._waiting:
            QApplication.processEvents()
            QThread.msleep(10)

        return self._char_result if self._char_result is not None else '\r'

    # ------------------------------------------------------------------
    # Screen API — misc
    # ------------------------------------------------------------------

    def get_size(self):
        return (ROWS, COLS)

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

    def reset(self):
        if self.transcript_file:
            self.close_transcript()
        if self.main_window:
            self.main_window.close()

    def exec(self):
        return self.app.exec()

    # ------------------------------------------------------------------
    # Menu actions
    # ------------------------------------------------------------------

    def open_game(self):
        path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Open Z-Machine Game", "",
            "Z-Machine Games (*.dat *.z3 *.z4 *.z5 *.z6 *.z7);;All Files (*.*)")
        if path:
            self.print_str(f"\n[Loading: {path}]\n")
            self.file_to_load = path

    def save_game(self):
        path, _ = QFileDialog.getSaveFileName(
            self.main_window, "Save Game", "save.qzl",
            "Quetzal Save (*.qzl);;All Files (*.*)")
        if path:
            self.print_str(f"\n[Saving to: {path}]\n")

    def restore_game(self):
        path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Restore Game", "",
            "Quetzal Save (*.qzl);;All Files (*.*)")
        if path:
            self.print_str(f"\n[Restoring from: {path}]\n")

    def toggle_debug(self):
        if self.debug_window.isVisible():
            self.debug_window.hide()
        else:
            self.debug_window.show()

    def toggle_objects(self):
        if self.object_window.isVisible():
            self.object_window.hide()
        else:
            self.object_window.refresh()
            self.object_window.show()

    def toggle_globals(self):
        if self.globals_window.isVisible():
            self.globals_window.hide()
        else:
            self.globals_window.refresh()
            self.globals_window.show()

    def toggle_stack(self):
        if self.stack_window.isVisible():
            self.stack_window.hide()
        else:
            self.stack_window.refresh()
            self.stack_window.show()
