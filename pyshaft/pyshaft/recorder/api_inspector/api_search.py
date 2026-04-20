"""PyShaft API Inspector — Global search dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QHBoxLayout,
    QPushButton,
)

from pyshaft.recorder.theme import COLORS

if TYPE_CHECKING:
    from pyshaft.recorder.api_inspector.api_models import ApiWorkflow, ApiRequestStep


class ApiSearchDialog(QDialog):
    """Global search across collections, requests, payloads, and assertions."""
    
    result_selected = pyqtSignal(object) # ApiRequestStep

    def __init__(self, workflow: ApiWorkflow, parent=None) -> None:
        super().__init__(parent)
        self._workflow = workflow
        self.setWindowTitle("Global Search")
        self.setMinimumSize(600, 400)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Search input
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search for keywords in URL, Body, Assertions...")
        self._search_input.textChanged.connect(self._perform_search)
        self._search_input.setStyleSheet(f"background: {COLORS['bg_darkest']}; padding: 8px; font-size: 11pt;")
        layout.addWidget(self._search_input)

        # Results list
        self._results_list = QListWidget()
        self._results_list.setStyleSheet(f"background: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']};")
        self._results_list.itemDoubleClicked.connect(self._on_item_selected)
        layout.addWidget(self._results_list)

        self._status = QLabel("Type to start searching...")
        layout.addWidget(self._status)

    def _perform_search(self, text: str) -> None:
        self._results_list.clear()
        if not text or len(text) < 2:
            self._status.setText("Keep typing...")
            return

        text = text.lower()
        results_count = 0
        
        for step in self._workflow.all_steps:
            matches = []
            
            if text in step.name.lower(): matches.append("Name")
            if text in step.url.lower(): matches.append("URL")
            if step.payload and text in step.payload.lower(): matches.append("Body")
            
            for a in step.assertions:
                if text in a.path.lower() or text in str(a.expected).lower():
                    matches.append(f"Assertion ({a.path})")
            
            if matches:
                item = QListWidgetItem(f"{step.method} {step.name} — Matches: {', '.join(matches[:3])}")
                item.setData(Qt.ItemDataRole.UserRole, step)
                self._results_list.addItem(item)
                results_count += 1
        
        self._status.setText(f"Found {results_count} results.")

    def _on_item_selected(self, item: QListWidgetItem) -> None:
        step = item.data(Qt.ItemDataRole.UserRole)
        if step:
            self.result_selected.emit(step)
            self.accept()
