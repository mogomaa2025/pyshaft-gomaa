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
    QCompleter,
)
from PyQt6.QtGui import QTextCursor, QKeyEvent
from PyQt6.QtCore import QStringListModel

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
        self._scope = None  # ApiRequestStep | ApiFolder | None (None = whole workflow)
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
        
        # Setup Completer
        self._completer = QCompleter()
        self._completer.setWidget(self._code_edit)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        # PyShaft + Python Keywords
        keywords = [
            "api.request", "api.get", "api.post", "api.put", "api.delete", "api.patch",
            "assert_status", "assert_json", "extract_json", "save_variable",
            "import", "from", "def", "class", "self", "return", "if", "for", "in", "None", "True", "False"
        ]
        model = QStringListModel(keywords, self._completer)
        self._completer.setModel(model)
        self._completer.activated.connect(self._insert_completion)

        # Patch keyPressEvent for completion
        original_key_press = self._code_edit.keyPressEvent
        def keyPressEvent(event: QKeyEvent):
            if self._completer.popup().isVisible():
                if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Tab, Qt.Key.Key_Backtab, Qt.Key.Key_Escape):
                    event.ignore()
                    return
            
            is_shortcut = event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Space
            if not is_shortcut:
                original_key_press(event)

            ctrl_or_shift = event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
            if is_shortcut or (not ctrl_or_shift and event.text().isalnum()):
                completion_prefix = self._text_under_cursor()
                if completion_prefix != self._completer.completionPrefix():
                    self._completer.setCompletionPrefix(completion_prefix)
                    self._completer.popup().setCurrentIndex(self._completer.completionModel().index(0, 0))
                
                cr = self._code_edit.cursorRect()
                cr.setWidth(self._completer.popup().sizeHintForColumn(0) + self._completer.popup().verticalScrollBar().sizeHint().width())
                self._completer.complete(cr)
            else:
                self._completer.popup().hide()

        self._code_edit.keyPressEvent = keyPressEvent

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

    def _text_under_cursor(self) -> str:
        tc = self._code_edit.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def _insert_completion(self, completion: str) -> None:
        if self._completer.widget() != self._code_edit:
            return
        tc = self._code_edit.textCursor()
        extra = len(completion) - len(self._completer.completionPrefix())
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:])
        self._code_edit.setTextCursor(tc)

    def update_code(self, workflow: ApiWorkflow, scope=None) -> None:
        """Regenerate and display code for *scope* (step/folder) or the whole workflow.

        Args:
            workflow: The full ApiWorkflow (needed for context like base_url).
            scope:    ApiRequestStep | ApiFolder | None.  When None the full workflow
                      is used as the code target.
        """
        if self._code_edit.hasFocus():
            return  # Don't overwrite while user is typing

        self._workflow = workflow
        self._scope = scope
        self._is_updating = True
        mode = self._mode_combo.currentData()
        target = scope if scope is not None else workflow
        code = generate_api_code(target, mode=mode)
        self._code_edit.setPlainText(code)
        self._is_updating = False

        # Update dock / tab title to show the active scope
        from pyshaft.recorder.api_inspector.api_models import ApiFolder, ApiRequestStep
        if isinstance(scope, (ApiRequestStep, ApiFolder)):
            self.setWindowTitle(f"PyShaft Code — {scope.name}")
        else:
            self.setWindowTitle("PyShaft Code")

    def _on_text_changed(self) -> None:
        if not self._is_updating:
            self._sync_timer.start()

    def _on_sync_timeout(self) -> None:
        """Emit signal to attempt reverse sync in main window."""
        self.code_modified.emit(self._code_edit.toPlainText())

    def _on_mode_changed(self) -> None:
        if self._workflow:
            self.update_code(self._workflow, scope=self._scope)

    def _copy_to_clipboard(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._code_edit.toPlainText())
