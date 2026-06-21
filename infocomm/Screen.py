# Backward-compatibility shim — Screen.py now delegates to ScreenQt.
try:
    from ScreenQt import (
        ZMachineScreen,
        TerminalWidget,
        DebugWindow,
        ObjectWindow,
        GlobalsWindow,
        StackWindow,
    )
except ImportError:
    # PySide6 not available; Qt backend unusable but other backends still work.
    pass

from ScreenGrid import ROWS, COLS, STYLE_REVERSE, STYLE_BOLD, STYLE_EMPHASIS, STYLE_FIXED
