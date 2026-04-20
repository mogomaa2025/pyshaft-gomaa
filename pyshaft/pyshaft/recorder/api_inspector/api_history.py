"""PyShaft API Inspector — Request history dock."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDockWidget,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QLabel,
)

from pyshaft.recorder.theme import COLORS, FONTS

if TYPE_CHECKING:
    from pyshaft.recorder.api_inspector.api_models import ApiRequestStep


class ApiHistoryDock(QDockWidget):
    """Dock showing history of executed requests."""
    
    request_restored = pyqtSignal(object) # ApiRequestStep (cloned)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("History", parent)
        self.setObjectName("history_dock")
        self._history: list[dict[str, Any]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QHBoxLayout()
        header.addWidget(QLabel("PAST REQUESTS"))
        header.addStretch()
        self._btn_clear = QPushButton("🗑 Clear")
        self._btn_clear.setFixedSize(70, 26)
        self._btn_clear.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg_medium']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text_primary']};
                font-size: 11px;
            }}
            QPushButton:hover {{ background: {COLORS['accent_red']}44; border-color: {COLORS['accent_red']}; }}
        """)
        self._btn_clear.clicked.connect(self.clear_history)
        header.addWidget(self._btn_clear)
        layout.addLayout(header)

        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: {COLORS['bg_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {COLORS['bg_darkest']};
            }}
        """)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._list)
        
        self.setWidget(container)

    def add_entry(self, step: ApiRequestStep) -> None:
        """Add a run result to history."""
        import copy
        # Store a snapshot of the step as it was when run
        snapshot = copy.deepcopy(step)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        status = snapshot.last_status or 0
        color = COLORS['accent_green'] if 200 <= status < 300 else COLORS['accent_red']
        
        text = f"[{timestamp}] {snapshot.method} {snapshot.name}\nStatus: {status} | {snapshot.url[:40]}..."
        
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, snapshot)
        item.setForeground(Qt.GlobalColor.white)
        
        self._list.insertItem(0, item) # Newest at top
        
        # Limit history
        if self._list.count() > 50:
            self._list.takeItem(self._list.count() - 1)

    def clear_history(self) -> None:
        self._list.clear()

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        snapshot = item.data(Qt.ItemDataRole.UserRole)
        if snapshot:
            self.request_restored.emit(snapshot)
