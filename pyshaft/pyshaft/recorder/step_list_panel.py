"""PyShaft Recorder — Step List Panel (left sidebar).

Displays recorded steps as styled cards with drag-and-drop reordering.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QDrag, QFont, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QFrame, QMenu, QAbstractItemView,
    QLineEdit,
)

from pyshaft.recorder.models import RecordedStep, RecordingSession
from pyshaft.recorder.theme import COLORS, FONTS


class StepCard(QFrame):
    """A styled card widget representing a single recorded step."""

    delete_clicked = pyqtSignal(str)  # step_id
    edit_clicked = pyqtSignal(str)    # step_id
    duplicate_clicked = pyqtSignal(str)  # step_id

    def __init__(self, step: RecordedStep, index: int, parent=None):
        super().__init__(parent)
        self.step = step
        self.step_index = index
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Index badge
        cat_colors = {
            "action": COLORS["step_action"],
            "assert": COLORS["step_assert"],
            "nav": COLORS["step_nav"],
            "wait": COLORS["step_wait"],
        }
        badge_color = cat_colors.get(self.step.category, COLORS["step_action"])

        index_label = QLabel(str(self.step_index + 1))
        index_label.setFixedSize(24, 24)
        index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        index_label.setStyleSheet(f"""
            background-color: {badge_color};
            color: {COLORS['bg_darkest']};
            border-radius: 12px;
            font-weight: 700;
            font-size: {FONTS['size_xs']};
        """)
        layout.addWidget(index_label)

        # Step info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Action name
        action_label = QLabel(f"{self.step.icon}  {self.step.action}")
        action_label.setStyleSheet(f"""
            color: {badge_color};
            font-weight: 600;
            font-size: {FONTS['size_base']};
        """)
        info_layout.addWidget(action_label)

        # Locator detail
        detail = self.step.display_label
        detail_label = QLabel(detail)
        detail_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONTS['size_sm']};
            font-family: {FONTS['family_mono']};
        """)
        detail_label.setWordWrap(True)
        info_layout.addWidget(detail_label)

        layout.addLayout(info_layout, 1)

        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(6)

        # Edit button
        edit_btn = QPushButton("✎")
        edit_btn.setFixedSize(20, 20)
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: #FFFFFF;
                border: none;
                font-size: 14px;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_purple']};
                color: #FFFFFF;
            }}
        """)
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.step.id))
        edit_btn.setToolTip("Edit step")
        actions_layout.addWidget(edit_btn)

        # Delete button
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: #FFFFFF;
                border: none;
                font-size: 12px;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_red']};
                color: #FFFFFF;
            }}
        """)
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.step.id))
        del_btn.setToolTip("Delete step")
        actions_layout.addWidget(del_btn)

        layout.addLayout(actions_layout)

    def mouseDoubleClickEvent(self, event):
        self.edit_clicked.emit(self.step.id)
        super().mouseDoubleClickEvent(event)


class StepListPanel(QWidget):
    """Left sidebar showing recorded steps as cards with drag-and-drop."""

    step_selected = pyqtSignal(str)     # step_id
    step_deleted = pyqtSignal(str)      # step_id
    step_moved = pyqtSignal(int, int)   # from_index, to_index
    step_edited = pyqtSignal(str)       # step_id
    step_duplicated = pyqtSignal(str)   # step_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session: RecordingSession | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("panel_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        title = QLabel("📋 Steps")
        title.setObjectName("title")
        title.setStyleSheet(f"font-size: {FONTS['size_md']}; font-weight: 700;")
        header_layout.addWidget(title)

        self._count_label = QLabel("0")
        self._count_label.setStyleSheet(f"""
            background-color: {COLORS['accent_purple_dim']};
            color: {COLORS['text_primary']};
            border-radius: 10px;
            padding: 2px 8px;
            font-size: {FONTS['size_xs']};
            font-weight: 700;
        """)
        header_layout.addWidget(self._count_label)
        header_layout.addStretch()

        # Clear all button
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_muted']};
                border: none;
                font-size: {FONTS['size_sm']};
            }}
            QPushButton:hover {{
                color: {COLORS['accent_red']};
            }}
        """)
        clear_btn.clicked.connect(self._clear_all)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        # Step list
        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setSpacing(4)
        self._list.setFrameShape(QFrame.Shape.NoFrame)
        self._list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_darkest']};
                border: none;
                padding: 8px;
            }}
            QListWidget::item {{
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }}
        """)
        self._list.currentRowChanged.connect(self._on_item_selected)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.model().rowsMoved.connect(self._on_rows_moved)
        layout.addWidget(self._list)

        # Empty state
        self._empty_label = QLabel("Click Record to start\ncapturing test steps")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: {FONTS['size_base']};
            padding: 40px;
        """)
        layout.addWidget(self._empty_label)

    def set_session(self, session: RecordingSession):
        """Set the recording session and refresh the list."""
        self._session = session
        self.refresh()

    def refresh(self):
        """Rebuild the step list from the session."""
        self._list.clear()

        if not self._session or not self._session.steps:
            self._empty_label.setVisible(True)
            self._list.setVisible(False)
            self._count_label.setText("0")
            return

        self._empty_label.setVisible(False)
        self._list.setVisible(True)
        self._count_label.setText(str(len(self._session.steps)))

        for i, step in enumerate(self._session.steps):
            card = StepCard(step, i)
            card.delete_clicked.connect(self._on_delete_step)
            card.edit_clicked.connect(self._on_edit_step)

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, step.id)
            item.setSizeHint(card.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, card)

    def add_step(self, step: RecordedStep):
        """Add a new step to the list (called during recording)."""
        if self._session:
            self._session.add_step(step)
            self.refresh()
            # Scroll to bottom
            self._list.scrollToBottom()

    def _on_item_selected(self, row: int):
        if row >= 0 and self._session and row < len(self._session.steps):
            self.step_selected.emit(self._session.steps[row].id)

    def _on_delete_step(self, step_id: str):
        self.step_deleted.emit(step_id)

    def _on_edit_step(self, step_id: str):
        self.step_edited.emit(step_id)

    def _on_rows_moved(self, *args):
        """Handle drag-and-drop reorder."""
        # Rebuild session order from list widget
        if not self._session:
            return
        new_order = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            step_id = item.data(Qt.ItemDataRole.UserRole)
            step = self._session.get_step(step_id)
            if step:
                new_order.append(step)
        self._session.steps = new_order
        self.refresh()

    def _show_context_menu(self, pos):
        item = self._list.itemAt(pos)
        if not item:
            return

        step_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['bg_medium']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['accent_purple']};
            }}
        """)

        edit_action = menu.addAction("✎  Edit Step")
        dup_action = menu.addAction("⧉  Duplicate")
        menu.addSeparator()
        del_action = menu.addAction("✕  Delete")
        del_action.setShortcut("Del")

        action = menu.exec(self._list.mapToGlobal(pos))
        if action == edit_action:
            self.step_edited.emit(step_id)
        elif action == dup_action:
            self.step_duplicated.emit(step_id)
        elif action == del_action:
            self.step_deleted.emit(step_id)

    def _clear_all(self):
        if self._session:
            self._session.steps.clear()
            self.refresh()
