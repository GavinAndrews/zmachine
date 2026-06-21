"""
ScreenQt.py — Qt GUI backend (PySide6).

TerminalWidget renders a ScreenGrid via QPainter.  All Z-machine window logic
lives in ScreenGrid; this file only handles Qt input/output and the event loop.
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QScrollArea, QSplitter,
    QVBoxLayout, QHBoxLayout, QTextEdit, QPlainTextEdit, QListWidget,
    QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
    QPushButton, QFileDialog, QLabel, QLineEdit, QTextBrowser,
    QAbstractItemView,
)
from PySide6.QtCore  import Qt, QTimer, QThread, QObject, QEvent
from PySide6.QtGui   import QFont, QFontMetrics, QPainter, QColor

from ScreenBase import ScreenBase
from ScreenGrid import ScreenGrid, ROWS, COLS, STYLE_REVERSE, STYLE_BOLD, STYLE_EMPHASIS


# ---------------------------------------------------------------------------
# Qt rendering widget
# ---------------------------------------------------------------------------

class TerminalWidget(QWidget):
    """Renders a ScreenGrid via QPainter and forwards keyboard input."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._font = QFont("Courier New", 11)
        fm = QFontMetrics(self._font)
        self._cw = fm.horizontalAdvance('X')
        self._ch = fm.height()
        self.setFixedSize(COLS * self._cw, ROWS * self._ch)
        self.setStyleSheet("background: black;")

        self._sg = ScreenGrid()

        # Input state
        self._input_mode   = False
        self._input_buffer = ""
        self._input_max    = COLS
        self._char_mode    = False

        # Callbacks → ZMachineScreen
        self.on_line_entered = None
        self.on_char_entered = None

        self._cursor_phase = True
        self._blink = QTimer(self)
        self._blink.timeout.connect(self._tick)
        self._blink.start(500)

    def _tick(self):
        if self._input_mode or self._char_mode:
            self._cursor_phase = not self._cursor_phase
            self.update()

    # -- delegation to ScreenGrid -----------------------------------------

    def split_window(self, height):
        self._sg.split_window(height)
        self.update()

    def set_window(self, win):
        self._sg.set_window(win)

    def set_cursor(self, row, col):
        self._sg.set_cursor(row, col)

    def get_cursor(self):
        return self._sg.get_cursor()

    def set_text_style(self, style):
        self._sg.set_text_style(style)

    def erase_window(self, win):
        self._sg.erase_window(win)
        self.update()

    def erase_line(self):
        self._sg.erase_line()
        self.update()

    def print_str(self, s):
        self._sg.print_str(s)
        self.update()

    # -- input ------------------------------------------------------------

    def start_line_input(self, max_chars=COLS):
        self._input_mode   = True
        self._input_buffer = ""
        self._input_max    = max_chars
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
            self._sg.print_str('\n')
            self.update()
            if self.on_line_entered:
                self.on_line_entered(text)
        elif key == Qt.Key.Key_Backspace:
            if self._input_buffer:
                self._input_buffer = self._input_buffer[:-1]
                sg = self._sg
                sg._lo_col -= 1
                if sg._lo_col < 0:
                    sg._lo_col = COLS - 1
                    sg._lo_row = max(sg._upper_rows, sg._lo_row - 1)
                sg._put(sg._lo_row, sg._lo_col, ' ', 0)
                self.update()
        else:
            ch = event.text()
            if ch and ch.isprintable() and len(self._input_buffer) < self._input_max - 1:
                self._input_buffer += ch
                self._sg.print_str(ch)
                self.update()

    def _key_char(self, event):
        self._char_mode = False
        key  = event.key()
        text = event.text()
        _MAP = {
            Qt.Key.Key_Return:    '\r',
            Qt.Key.Key_Enter:     '\r',
            Qt.Key.Key_Escape:    '\x1b',
            Qt.Key.Key_Backspace: '\x08',
            Qt.Key.Key_Delete:    '\x7f',
            Qt.Key.Key_Up:        '\x1b[A',
            Qt.Key.Key_Down:      '\x1b[B',
            Qt.Key.Key_Right:     '\x1b[C',
            Qt.Key.Key_Left:      '\x1b[D',
        }
        result = _MAP.get(key, text if (text and text.isprintable()) else '\r')
        self.update()
        if self.on_char_entered:
            self.on_char_entered(result)

    # -- painting ---------------------------------------------------------

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setFont(self._font)
        fm     = QFontMetrics(self._font)
        ascent = fm.ascent()
        cw, ch = self._cw, self._ch
        BLACK  = QColor(0, 0, 0)
        WHITE  = QColor(204, 204, 204)
        BRITE  = QColor(255, 255, 255)

        for r in range(ROWS):
            for c in range(COLS):
                cell = self._sg._grid[r][c]
                x = c * cw
                y = r * ch
                if cell.style & STYLE_REVERSE:
                    bg, fg = WHITE, BLACK
                else:
                    bg, fg = BLACK, WHITE
                painter.fillRect(x, y, cw, ch, bg)
                if cell.char != ' ':
                    painter.setPen(fg)
                    painter.drawText(x, y + ascent, cell.char)

        if (self._input_mode or self._char_mode) and self._cursor_phase:
            sg = self._sg
            x  = sg._lo_col * cw
            y  = sg._lo_row * ch
            painter.fillRect(x, y, cw, ch, BRITE)
            char = sg._grid[sg._lo_row][sg._lo_col].char
            if char != ' ':
                painter.setPen(BLACK)
                painter.drawText(x, y + ascent, char)

        painter.end()


# ---------------------------------------------------------------------------
# Debug / inspector windows
# ---------------------------------------------------------------------------

class TraceWindow(QWidget):
    """Scrollable instruction trace log, capped at 1000 lines, with optional file export."""

    MAX_LINES = 1000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Instruction Trace")
        self.setGeometry(750, 100, 650, 500)
        self._log_file = None

        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._text.clear if hasattr(self, '_text') else lambda: None)
        self._pause_btn = QPushButton("Pause")
        self._pause_btn.setCheckable(True)
        file_lbl = QLabel("Log file:")
        self._file_edit = QLineEdit("trace.log")
        self._file_edit.setFixedWidth(160)
        self._log_btn = QPushButton("Start logging")
        self._log_btn.setCheckable(True)
        self._log_btn.clicked.connect(self._toggle_log)
        toolbar.addWidget(clear_btn)
        toolbar.addWidget(self._pause_btn)
        toolbar.addStretch()
        toolbar.addWidget(file_lbl)
        toolbar.addWidget(self._file_edit)
        toolbar.addWidget(self._log_btn)
        layout.addLayout(toolbar)

        # Trace pane
        self._text = QPlainTextEdit()
        self._text.setFont(QFont("Courier New", 9))
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(self.MAX_LINES)
        self._text.setStyleSheet(
            "QPlainTextEdit { background: #0a0a0a; color: #b0b0b0; border: none; }")
        layout.addWidget(self._text)

        # Fix the clear button now that _text exists
        clear_btn.clicked.disconnect()
        clear_btn.clicked.connect(self._text.clear)

    def add(self, pc, name, args):
        """Called for every instruction.  Fast-path exits when nothing is active."""
        if self._pause_btn.isChecked():
            return
        if not self.isVisible() and self._log_file is None:
            return

        arg_str = ' '.join(f'${a:04X}' for a in args) if args else ''
        line = f'@{pc:05X}  {name:<16}{arg_str}'

        if self.isVisible():
            sb = self._text.verticalScrollBar()
            at_bottom = sb.value() >= sb.maximum() - 4
            self._text.appendPlainText(line)
            if at_bottom:
                sb.setValue(sb.maximum())

        if self._log_file is not None:
            try:
                self._log_file.write(line + '\n')
                self._log_file.flush()
            except Exception:
                self._close_log()

    def _toggle_log(self, checked):
        if checked:
            path = self._file_edit.text().strip() or 'trace.log'
            try:
                self._log_file = open(path, 'a', encoding='utf-8')
                self._log_btn.setText('Stop logging')
                self._file_edit.setEnabled(False)
            except OSError as e:
                self._log_btn.setChecked(False)
                self._log_btn.setText(f'Error: {e}')
        else:
            self._close_log()

    def _close_log(self):
        if self._log_file:
            self._log_file.close()
            self._log_file = None
        self._log_btn.setChecked(False)
        self._log_btn.setText('Start logging')
        self._file_edit.setEnabled(True)

    def closeEvent(self, event):
        self._close_log()
        event.accept()


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
        pause_btn.clicked.connect(self._toggle)
        toolbar.addWidget(clear_btn)
        toolbar.addWidget(pause_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.text_area = QTextEdit()
        self.text_area.setFont(QFont("Courier New", 9))
        self.text_area.setReadOnly(True)
        layout.addWidget(self.text_area)
        self.paused = False

    def _toggle(self, checked): self.paused = checked

    def append(self, text, color='white'):
        if self.paused:
            return
        self.text_area.setTextColor(QColor(color))
        self.text_area.append(text)
        self.text_area.ensureCursorVisible()


class ObjectWindow(QWidget):
    """Object tree browser with property inspector and clickable navigation."""

    def __init__(self, processor=None, parent=None):
        super().__init__(parent)
        self.processor = processor
        self.setWindowTitle("Object State")
        self.setGeometry(100, 100, 1000, 600)
        self._items = {}   # obj_num → QTreeWidgetItem

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # ── toolbar ──────────────────────────────────────────────────────
        bar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        expand_btn  = QPushButton("Expand all")
        expand_btn.clicked.connect(lambda: self._tree.expandAll())
        collapse_btn = QPushButton("Collapse all")
        collapse_btn.clicked.connect(lambda: self._tree.collapseAll())
        self._goto_edit = QLineEdit()
        self._goto_edit.setPlaceholderText("Go to object #")
        self._goto_edit.setFixedWidth(120)
        self._goto_edit.returnPressed.connect(self._goto_obj)
        goto_btn = QPushButton("Go")
        goto_btn.clicked.connect(self._goto_obj)
        bar.addWidget(refresh_btn)
        bar.addWidget(expand_btn)
        bar.addWidget(collapse_btn)
        bar.addStretch()
        bar.addWidget(QLabel("Object #:"))
        bar.addWidget(self._goto_edit)
        bar.addWidget(goto_btn)
        layout.addLayout(bar)

        # ── splitter: tree (left) + detail (right) ───────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["#", "Name", "Attributes set"])
        self._tree.setColumnWidth(0, 60)
        self._tree.setColumnWidth(1, 220)
        self._tree.setFont(QFont("Courier New", 9))
        self._tree.itemSelectionChanged.connect(self._on_select)
        splitter.addWidget(self._tree)

        self._detail = QTextBrowser()
        self._detail.setFont(QFont("Courier New", 9))
        self._detail.setOpenLinks(False)
        self._detail.anchorClicked.connect(self._on_link)
        splitter.addWidget(self._detail)

        splitter.setSizes([420, 580])
        layout.addWidget(splitter)

    # ── tree building ─────────────────────────────────────────────────────

    def refresh(self):
        self._tree.clear()
        self._items.clear()
        if not self.processor:
            return

        ot  = self.processor.object_table
        mem = self.processor.memory

        # Build all item nodes
        raw = {}  # obj_num → (ObjectTableEntry, QTreeWidgetItem)
        for i in range(1, ot.object_count + 1):
            try:
                obj  = ot.get_object_table_entry(i)
                name = obj.get_property_table().get_description().strip() or f"(#{i})"
                attrs = self._attr_str(obj)
                item = QTreeWidgetItem([str(i), name, attrs])
                item.setData(0, Qt.ItemDataRole.UserRole, i)
                raw[i] = (obj, item)
                self._items[i] = item
            except Exception:
                continue

        # Insert into tree following the child→sibling chains so order matches
        # the Z-machine object tree exactly.
        visited = set()

        def add_subtree(parent_item, obj_num):
            if obj_num == 0 or obj_num in visited or obj_num not in raw:
                return
            visited.add(obj_num)
            obj, item = raw[obj_num]
            if parent_item is None:
                self._tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            add_subtree(item,        obj.get_child_object_number())
            add_subtree(parent_item, obj.get_next_sibling_object_number())

        for i, (obj, _) in raw.items():
            if obj.get_parent_object_number() == 0 and i not in visited:
                add_subtree(None, i)

        # Any orphaned objects (corrupt tree) go to top level
        for i, (_, item) in raw.items():
            if i not in visited:
                self._tree.addTopLevelItem(item)

    def _attr_str(self, obj):
        max_attr = 48 if obj.game_version >= 4 else 32
        return ', '.join(
            str(a) for a in range(max_attr) if obj.test_attr(a)
        )

    # ── selection / navigation ────────────────────────────────────────────

    def _on_select(self):
        sel = self._tree.selectedItems()
        if sel:
            self._show_detail(sel[0].data(0, Qt.ItemDataRole.UserRole))

    def _goto_obj(self):
        try:
            n = int(self._goto_edit.text().strip())
        except ValueError:
            return
        item = self._items.get(n)
        if item:
            self._tree.setCurrentItem(item)
            self._tree.scrollToItem(
                item, QAbstractItemView.ScrollHint.PositionAtCenter)

    def _on_link(self, url):
        if url.scheme() == 'obj':
            try:
                n = int(url.path().lstrip('/'))
                item = self._items.get(n)
                if item:
                    self._tree.setCurrentItem(item)
                    self._tree.scrollToItem(
                        item, QAbstractItemView.ScrollHint.PositionAtCenter)
            except (ValueError, AttributeError):
                pass

    # ── detail panel ─────────────────────────────────────────────────────

    def _obj_link(self, n, ot):
        if n == 0:
            return '<i>none</i>'
        try:
            desc = ot.get_object_table_entry(n).get_property_table() \
                     .get_description().strip() or '?'
        except Exception:
            desc = '?'
        return f'<a href="obj:/{n}">{n}: {desc}</a>'

    def _show_detail(self, obj_num):
        if not self.processor or not obj_num:
            return
        ot  = self.processor.object_table
        mem = self.processor.memory
        try:
            obj  = ot.get_object_table_entry(obj_num)
            pt   = obj.get_property_table()
            name = pt.get_description().strip() or '(no name)'

            parent_n  = obj.get_parent_object_number()
            child_n   = obj.get_child_object_number()
            sibling_n = obj.get_next_sibling_object_number()

            # Collect all children for display
            children = []
            c = child_n
            while c:
                children.append(c)
                try:
                    c = ot.get_object_table_entry(c).get_next_sibling_object_number()
                except Exception:
                    break

            h = [f'<b>Object #{obj_num}</b> &mdash; &ldquo;{name}&rdquo;',
                 '<hr>',
                 f'<b>Parent:</b>  {self._obj_link(parent_n, ot)}<br>',
                 f'<b>Sibling:</b> {self._obj_link(sibling_n, ot)}<br>',
                 f'<b>Child:</b>   {self._obj_link(child_n, ot)}']

            if len(children) > 1:
                h.append('<br><b>All children:</b><br>')
                for c in children:
                    h.append(f'&nbsp;&nbsp;{self._obj_link(c, ot)}<br>')

            # Attributes
            max_attr = 48 if obj.game_version >= 4 else 32
            set_attrs = [a for a in range(max_attr) if obj.test_attr(a)]
            h.append('<hr><b>Attributes set:</b> ')
            h.append(', '.join(str(a) for a in set_attrs) if set_attrs else '<i>none</i>')

            # Properties
            h.append('<hr><b>Properties:</b><br>')
            h.append('<table cellspacing="0" cellpadding="2">'
                     '<tr><th align="left">#</th><th align="left">Len</th>'
                     '<th align="left">Bytes</th><th align="left">Value</th></tr>')

            prop = pt.find_first_property()
            if prop is None:
                h.append('</table><i>none</i>')
            else:
                while prop is not None:
                    n  = prop.get_property_number()
                    ln = prop.get_length()
                    da = prop.get_data_address()
                    raw_bytes = [mem[da + k] for k in range(ln)]
                    hex_str   = ' '.join(f'${b:02X}' for b in raw_bytes)
                    if ln == 1:
                        val_str = f'{raw_bytes[0]} / ${raw_bytes[0]:02X}'
                    elif ln == 2:
                        v = (raw_bytes[0] << 8) | raw_bytes[1]
                        val_str = f'{v} / ${v:04X}'
                    else:
                        val_str = ''
                    h.append(f'<tr><td>{n}</td><td>{ln}</td>'
                             f'<td><code>{hex_str}</code></td>'
                             f'<td>{val_str}</td></tr>')
                    prop = pt.find_next_property(prop)
                h.append('</table>')

            self._detail.setHtml(''.join(h))
        except Exception as e:
            self._detail.setPlainText(f'Error reading object #{obj_num}: {e}')


class GlobalsWindow(QWidget):
    def __init__(self, processor=None, parent=None):
        super().__init__(parent)
        self.processor = processor
        self.setWindowTitle("Global Variables")
        self.setGeometry(100, 100, 400, 300)
        layout = QVBoxLayout(self)
        btn = QPushButton("Refresh"); btn.clicked.connect(self.refresh)
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
        btn = QPushButton("Refresh"); btn.clicked.connect(self.refresh)
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
# ZMachineScreen — public screen interface, owns Qt event loop
# ---------------------------------------------------------------------------

class ZMachineScreen(ScreenBase):

    def __init__(self):
        super().__init__()
        self.app            = QApplication.instance() or QApplication(sys.argv)
        self.main_window    = None
        self.terminal       = None
        self.debug_window   = None
        self.object_window  = None
        self.globals_window = None
        self.stack_window   = None
        self.trace_window   = None
        self._running       = False
        self._line_result   = None
        self._char_result   = None
        self._waiting       = False
        self._show_debug    = False   # set True before run() to open debug windows

    def init(self):
        self.main_window = QMainWindow()
        self.main_window.setWindowTitle("Infocomm Z-Machine Interpreter")

        menubar = self.main_window.menuBar()
        fm = menubar.addMenu("File")
        fm.addAction("Open Game...",  self.open_game)
        fm.addAction("Save Game",     self.save_game)
        fm.addAction("Restore Game",  self.restore_game)
        fm.addSeparator()
        fm.addAction("Exit", self.app.quit)
        vm = menubar.addMenu("View")
        vm.addAction("Debug Log",        self.toggle_debug)
        vm.addAction("Instruction Trace",self.toggle_trace)
        vm.addAction("Objects",          self.toggle_objects)
        vm.addAction("Globals",          self.toggle_globals)
        vm.addAction("Stack",            self.toggle_stack)

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
        self.trace_window   = TraceWindow()
        self.object_window  = ObjectWindow(self.processor)
        self.globals_window = GlobalsWindow(self.processor)
        self.stack_window   = StackWindow(self.processor)

        if self._show_debug:
            self.debug_window.show()
            self.object_window.show()
            self.globals_window.show()
            self.stack_window.show()

        self.terminal.setFocus()

        # When the main window is closed (X button), call app.quit() so that
        # all child/debug windows also close and aboutToQuit fires.
        # Without this, other open windows keep Qt alive and _on_quit never fires.
        class _MainClose(QObject):
            def __init__(self, app):
                super().__init__()
                self._app = app
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.Close:
                    self._app.quit()
                return False  # let the event proceed normally

        self._main_close_filter = _MainClose(self.app)
        self.main_window.installEventFilter(self._main_close_filter)

        # Ensure the process exits cleanly when the window is closed, even if
        # the interpreter is blocked in a read_line / read_char spin loop.
        self.app.aboutToQuit.connect(self._on_quit)

    def _on_quit(self):
        self._running = False
        self._waiting = False
        if self.terminal:
            self.terminal._input_mode = False
            self.terminal._char_mode  = False

    def reset(self):
        if self.transcript_file:
            self.close_transcript()
        if self.main_window:
            self.main_window.close()

    def _cb_line(self, text):
        self._line_result = text
        self._waiting     = False

    def _cb_char(self, ch):
        self._char_result = ch
        self._waiting     = False

    def _bind_debug_windows(self):
        if self.object_window:
            self.object_window.processor  = self.processor
            self.globals_window.processor = self.processor
            self.stack_window.processor   = self.processor
        self._bind_trace()

    def _bind_trace(self):
        if self.processor and self.trace_window:
            self.processor.instructions.trace_callback = self.trace_window.add

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def print_str(self, s: str):
        if self.terminal:
            self.terminal.print_str(s)
        if self.stream2_active and self.transcript_file:
            self.transcript_file.write(s)
        if self.debug_window and self.debug_window.isVisible():
            win = self.terminal._sg._current_win if self.terminal else 0
            pc  = ''
            if self.processor and hasattr(self.processor, 'instructions'):
                pc = f"@{self.processor.instructions._current_opcode_pc:05X} "
            self.debug_window.append(f"{pc}[W{win}] {repr(s)}", color='yellow')

    def split_window(self, height: int):
        if self.terminal:
            self.terminal.split_window(height)
        if self.debug_window:
            self.debug_window.append(f"[SPLIT_WINDOW {height}]", color='cyan')

    def set_window(self, win: int):
        if self.terminal:
            self.terminal.set_window(win)
        if self.debug_window:
            self.debug_window.append(f"[SET_WINDOW {win}]", color='cyan')

    def set_cursor(self, row: int, col: int):
        if self.terminal:
            self.terminal.set_cursor(row, col)

    def get_cursor(self):
        return self.terminal.get_cursor() if self.terminal else (1, 1)

    def set_text_style(self, style: int):
        if self.terminal:
            self.terminal.set_text_style(style)

    def erase_window(self, win: int):
        if self.terminal:
            self.terminal.erase_window(win)
        if self.debug_window:
            self.debug_window.append(f"[ERASE_WINDOW {win}]", color='cyan')

    def erase_line(self):
        if self.terminal:
            self.terminal.erase_line()

    def refresh(self):
        QApplication.processEvents()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def read_line(self, max_chars, time_tenths=0, time_routine_cb=None):
        self._line_result = None
        self._waiting     = True
        if self.terminal:
            self.terminal.start_line_input(max_chars)
        if time_tenths > 0 and time_routine_cb:
            def _t():
                if self._waiting and time_routine_cb():
                    self._line_result = ""
                    self._waiting     = False
                    if self.terminal:
                        self.terminal._input_mode = False
            QTimer.singleShot(time_tenths * 100, _t)
        while self._waiting and self._running:
            QApplication.processEvents()
            QThread.msleep(10)
        if not self._running:
            raise SystemExit(0)
        return self._line_result if self._line_result is not None else ""

    def read_char(self, time_tenths=0, time_routine_cb=None):
        self._char_result = None
        self._waiting     = True
        if self.terminal:
            self.terminal.start_char_input()
        if time_tenths > 0 and time_routine_cb:
            def _t():
                if self._waiting and time_routine_cb():
                    self._char_result = '\r'
                    self._waiting     = False
                    if self.terminal:
                        self.terminal._char_mode = False
            QTimer.singleShot(time_tenths * 100, _t)
        while self._waiting and self._running:
            QApplication.processEvents()
            QThread.msleep(10)
        if not self._running:
            raise SystemExit(0)
        return self._char_result if self._char_result is not None else '\r'

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------

    def run(self, processor):
        from Instructions import _UndoPerformed, _RestartRequested
        from Machine import build_machine

        self.processor = processor
        self._bind_debug_windows()
        self._running  = True

        def _step():
            nonlocal processor
            if not self._running:
                return
            try:
                processor.next_instruction()
            except _UndoPerformed:
                pass
            except _RestartRequested:
                undo_rc = processor.instructions.undo_random_continue
                self.erase_window(-1)
                processor = build_machine(
                    processor.filename, self,
                    scripting=None, seed=self._seed,
                )
                processor.instructions.undo_random_continue = undo_rc
                self.processor = processor
                self._bind_debug_windows()
            except SystemExit:
                self._running = False
                self.app.quit()
                return
            except KeyboardInterrupt:
                self._running = False
                self.app.quit()
                return
            except Exception:
                import traceback
                traceback.print_exc()
                self._running = False
                self.app.quit()
                return
            if self._running:
                QTimer.singleShot(1, _step)

        QTimer.singleShot(10, _step)
        try:
            self.app.exec()
        except Exception:
            pass
        finally:
            self.reset()
            self._running = False

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def get_size(self):
        return (ROWS, COLS)

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
        if self.debug_window.isVisible(): self.debug_window.hide()
        else: self.debug_window.show()

    def toggle_trace(self):
        if self.trace_window.isVisible(): self.trace_window.hide()
        else: self.trace_window.show()

    def toggle_objects(self):
        if self.object_window.isVisible(): self.object_window.hide()
        else: self.object_window.refresh(); self.object_window.show()

    def toggle_globals(self):
        if self.globals_window.isVisible(): self.globals_window.hide()
        else: self.globals_window.refresh(); self.globals_window.show()

    def toggle_stack(self):
        if self.stack_window.isVisible(): self.stack_window.hide()
        else: self.stack_window.refresh(); self.stack_window.show()
