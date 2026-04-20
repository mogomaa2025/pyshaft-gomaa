"""PyShaft Recorder — Command Palette (Ctrl+K).

Quick-search dialog for actions, assertions, and commands.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QHBoxLayout, QFrame,
)

from pyshaft.recorder.theme import COLORS, FONTS, ICONS


# All searchable commands
_COMMANDS = [
    # Actions
    {"id": "click",        "label": "Click",           "icon": ICONS["click"],      "category": "action",  "shortcut": ""},
    {"id": "double_click", "label": "Double Click",    "icon": ICONS["dblclick"],   "category": "action",  "shortcut": ""},
    {"id": "right_click",  "label": "Right Click",     "icon": ICONS["rightclick"], "category": "action",  "shortcut": ""},
    {"id": "type",         "label": "Type Text",       "icon": ICONS["type"],       "category": "action",  "shortcut": ""},
    {"id": "hover",        "label": "Hover",           "icon": ICONS["hover"],      "category": "action",  "shortcut": ""},
    {"id": "scroll",       "label": "Scroll To",       "icon": ICONS["scroll"],     "category": "action",  "shortcut": ""},
    {"id": "select",       "label": "Select Option",   "icon": ICONS["select"],     "category": "action",  "shortcut": ""},
    {"id": "check",        "label": "Check",           "icon": ICONS["check"],      "category": "action",  "shortcut": ""},
    {"id": "uncheck",      "label": "Uncheck",         "icon": ICONS["uncheck"],    "category": "action",  "shortcut": ""},
    {"id": "submit",       "label": "Submit Form",     "icon": ICONS["submit"],     "category": "action",  "shortcut": ""},
    {"id": "drag",         "label": "Drag & Drop",     "icon": ICONS["drag"],       "category": "action",  "shortcut": ""},
    {"id": "clear",        "label": "Clear Input",     "icon": "⌫",                "category": "action",  "shortcut": ""},
    # Assertions
    {"id": "assert_visible",       "label": "Assert Visible",        "icon": ICONS["visible"],  "category": "assert",  "shortcut": ""},
    {"id": "assert_hidden",        "label": "Assert Hidden",         "icon": ICONS["hidden"],   "category": "assert",  "shortcut": ""},
    {"id": "assert_text",          "label": "Assert Text",           "icon": ICONS["text"],     "category": "assert",  "shortcut": ""},
    {"id": "assert_enabled",       "label": "Assert Enabled",        "icon": ICONS["enabled"],  "category": "assert",  "shortcut": ""},
    {"id": "assert_disabled",      "label": "Assert Disabled",       "icon": ICONS["disabled"], "category": "assert",  "shortcut": ""},
    {"id": "assert_checked",       "label": "Assert Checked",        "icon": ICONS["check"],    "category": "assert",  "shortcut": ""},
    {"id": "assert_title",         "label": "Assert Page Title",     "icon": ICONS["title"],    "category": "assert",  "shortcut": ""},
    {"id": "assert_url",           "label": "Assert URL",            "icon": ICONS["url"],      "category": "assert",  "shortcut": ""},
    {"id": "assert_contain_text",  "label": "Assert Contains Text",  "icon": "⊃Aa",            "category": "assert",  "shortcut": ""},
    {"id": "assert_contain_title", "label": "Assert Contains Title", "icon": "⊃📄",            "category": "assert",  "shortcut": ""},
    {"id": "assert_contain_url",   "label": "Assert Contains URL",   "icon": "⊃🔗",            "category": "assert",  "shortcut": ""},
    # Utilities
    {"id": "open_url",    "label": "Open URL",        "icon": ICONS["nav"],    "category": "nav",    "shortcut": "Ctrl+O"},
    {"id": "go_back",     "label": "Go Back",         "icon": "←",            "category": "nav",    "shortcut": ""},
    {"id": "go_forward",  "label": "Go Forward",      "icon": "→",            "category": "nav",    "shortcut": ""},
    {"id": "refresh",     "label": "Refresh Page",    "icon": "↻",            "category": "nav",    "shortcut": ""},
    {"id": "screenshot",  "label": "Take Screenshot", "icon": "📸",           "category": "util",   "shortcut": ""},
    # Recorder controls
    {"id": "_record",     "label": "Start Recording",  "icon": ICONS["record"], "category": "control", "shortcut": "Ctrl+R"},
    {"id": "_stop",       "label": "Stop Recording",   "icon": ICONS["stop"],   "category": "control", "shortcut": "Ctrl+S"},
    {"id": "_inspect",    "label": "Toggle Inspector",  "icon": ICONS["inspect"],"category": "control", "shortcut": "Ctrl+I"},
    {"id": "_export",     "label": "Export Code",       "icon": ICONS["export"], "category": "control", "shortcut": "Ctrl+E"},
    {"id": "_pom",        "label": "Convert to POM",    "icon": ICONS["pom"],    "category": "control", "shortcut": "Ctrl+P"},
    {"id": "_undo",       "label": "Undo",              "icon": ICONS["undo"],   "category": "control", "shortcut": "Ctrl+Z"},
    {"id": "_redo",       "label": "Redo",              "icon": ICONS["redo"],   "category": "control", "shortcut": "Ctrl+Y"},
]


class CommandPalette(QDialog):
    """Ctrl+K command palette for quick-searching actions and commands."""

    command_selected = pyqtSignal(str)  # command_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setFixedWidth(480)
        self.setMaximumHeight(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container with border
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_medium']};
                border: 1px solid {COLORS['accent_purple']};
                border-radius: 12px;
            }}
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(4)

        # Search input
        self._search = QLineEdit()
        self._search.setPlaceholderText("  Type a command...")
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 16px;
                font-size: {FONTS['size_md']};
                color: {COLORS['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {COLORS['accent_purple']};
            }}
        """)
        self._search.textChanged.connect(self._filter_commands)
        self._search.returnPressed.connect(self._on_enter)
        container_layout.addWidget(self._search)

        # Results list
        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
                padding: 4px;
            }}
            QListWidget::item {{
                background-color: transparent;
                border-radius: 6px;
                padding: 8px 12px;
                margin: 1px 0;
                color: {COLORS['text_primary']};
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['accent_purple_dim']};
            }}
            QListWidget::item:hover:!selected {{
                background-color: {COLORS['bg_hover']};
            }}
        """)
        self._list.itemActivated.connect(self._on_item_activated)
        container_layout.addWidget(self._list)

        layout.addWidget(container)

        # Populate initial list
        self._filter_commands("")

    def _filter_commands(self, text: str):
        """Filter commands based on search text."""
        self._list.clear()
        search = text.lower().strip()

        category_colors = {
            "action": COLORS["step_action"],
            "assert": COLORS["step_assert"],
            "nav": COLORS["step_nav"],
            "control": COLORS["text_muted"],
            "util": COLORS["accent_blue"],
        }

        for cmd in _COMMANDS:
            # Fuzzy match: search in id, label, and category
            if search and not any(
                search in field.lower()
                for field in [cmd["id"], cmd["label"], cmd["category"]]
            ):
                continue

            color = category_colors.get(cmd["category"], COLORS["text_primary"])
            shortcut = f"  ({cmd['shortcut']})" if cmd["shortcut"] else ""

            item = QListWidgetItem(f"{cmd['icon']}  {cmd['label']}{shortcut}")
            item.setData(Qt.ItemDataRole.UserRole, cmd["id"])
            item.setToolTip(f"w.{cmd['id']}()" if not cmd["id"].startswith("_") else cmd["label"])
            self._list.addItem(item)

        # Select first item
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _on_enter(self):
        """Handle Enter key — select current item."""
        current = self._list.currentItem()
        if current:
            self._on_item_activated(current)

    def _on_item_activated(self, item: QListWidgetItem):
        """Handle item selection."""
        cmd_id = item.data(Qt.ItemDataRole.UserRole)
        self.command_selected.emit(cmd_id)
        self.close()

    def showEvent(self, event):
        """Focus the search input when shown."""
        super().showEvent(event)
        self._search.clear()
        self._search.setFocus()
        self._filter_commands("")

    def keyPressEvent(self, event):
        """Handle keyboard navigation."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            # Forward to list
            self._list.keyPressEvent(event)
        else:
            super().keyPressEvent(event)
