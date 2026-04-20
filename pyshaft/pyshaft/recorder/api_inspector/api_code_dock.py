"""PyShaft API Inspector — Code preview dock with POM support and bidirectional highlighting."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyshaft.recorder.api_inspector.api_code_generator import generate_api_code
from pyshaft.recorder.api_inspector.api_highlighter import ApiSyntaxHighlighter
from pyshaft.recorder.theme import COLORS, FONTS

if TYPE_CHECKING:
    from pyshaft.recorder.api_inspector.api_models import ApiWorkflow


class ApiCodeDock(QDockWidget):
    """Dockable panel for live PyShaft code preview with Script/POM modes."""
    
    code_modified = pyqtSignal(str) # Emitted when manual edits occur

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("PyShaft Code", parent)
        self.setObjectName("code_dock")
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self._workflow: ApiWorkflow | None = None
        self._is_updating = False
        
        self._sync_timer = QTimer()
        self._sync_timer.setSingleShot(True)
        self._sync_timer.setInterval(2000) # 2s debounce for reverse sync
        self._sync_timer.timeout.connect(self._on_sync_timeout)
        
        self._build_ui()

    def _build_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        
        toolbar = QHBoxLayout()
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("📄 Test Script", "test")
        self._mode_combo.addItem("🏗 Page Object (POM)", "pom")
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        toolbar.addWidget(self._mode_combo)
        
        btn_copy = QPushButton("📋 Copy Code")
        btn_copy.clicked.connect(self._copy_to_clipboard)
        toolbar.addWidget(btn_copy)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._code_edit = QPlainTextEdit()
        self._code_highlighter = ApiSyntaxHighlighter(self._code_edit.document(), mode="python")
        self._code_edit.textChanged.connect(self._on_text_changed)
        
        font = self._code_edit.font()
        font.setFamily(FONTS['family_mono'])
        font.setPointSize(10)
        self._code_edit.setFont(font)
        
        self._code_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {COLORS['bg_darkest']};
                border: 1px solid {COLORS['border']};
                color: {COLORS['text_primary']};
                padding: 8px;
            }}
        """)
        layout.addWidget(self._code_edit)
        self.setWidget(container)

    def update_code(self, workflow: ApiWorkflow) -> None:
        """Regenerate and display code for the current workflow."""
        if self._code_edit.hasFocus(): return # Don't overwrite if user is typing
        
        self._workflow = workflow
        self._is_updating = True
        mode = self._mode_combo.currentData()
        code = generate_api_code(workflow, mode=mode)
        self._code_edit.setPlainText(code)
        self._is_updating = False

    def _on_text_changed(self) -> None:
        if not self._is_updating:
            self._sync_timer.start()

    def _on_sync_timeout(self) -> None:
        """Emit signal to attempt reverse sync in main window."""
        self.code_modified.emit(self._code_edit.toPlainText())

    def _on_mode_changed(self) -> None:
        if self._workflow: self.update_code(self._workflow)

    def _copy_to_clipboard(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._code_edit.toPlainText())
