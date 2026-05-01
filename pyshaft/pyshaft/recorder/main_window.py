"""PyShaft Recorder — Main Window.

3-panel layout: Step List (left), Integrated Browser (center), Inspector (right).
Bottom panel: Code Output / Workflow Diagram.

Default mode: Inspector-first.  Users browse, click elements → popup appears
with locator choices and action/assertion buttons → step is created.
Recording mode auto-captures events and is toggled separately.
"""

from __future__ import annotations

import json
import logging
import time
from functools import partial
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QUrl, QRect
from PyQt6.QtGui import QAction, QKeySequence, QFont, QPixmap
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QFrame, QPushButton, QLabel, QLineEdit, QTabWidget,
    QPlainTextEdit, QMenuBar, QToolBar, QStatusBar, QFileDialog,
    QInputDialog, QMessageBox, QComboBox, QApplication, QMenu,
    QToolButton,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

from pyshaft.recorder.models import RecordedStep, RecordingSession, LocatorSuggestion
from pyshaft.recorder.step_list_panel import StepListPanel
from pyshaft.recorder.inspector_panel import InspectorPanel
from pyshaft.recorder.element_popup import ElementActionPopup
from pyshaft.recorder.workflow_view import WorkflowView
from pyshaft.recorder.command_palette import CommandPalette
from pyshaft.recorder.code_generator import generate_code
from pyshaft.recorder.io_manager import IOManager
from pyshaft.recorder.theme import COLORS, FONTS, ICONS

logger = logging.getLogger("pyshaft.recorder.main_window")


from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWebEngineCore import QWebEnginePage

class RecorderWebPage(QWebEnginePage):
    """Subclass of QWebEnginePage to intercept JavaScript console messages.
    
    In PyQt6, consoleMessage is a virtual method that must be overridden,
    not a signal we can connect to directly.
    """
    console_message = pyqtSignal(int, str, int, str)

    def javaScriptConsoleMessage(self, level, message, line, source):
        # Emit our custom signal so MainWindow can handle it
        self.console_message.emit(level, message, line, source)
        # Call base implementation (optional, usually just prints to stdout in debug)
        super().javaScriptConsoleMessage(level, message, line, source)


# ── Custom Widgets ───────────────────────────────────────────────────────
class DockTitleBar(QWidget):
    def __init__(self, title: str, dock: QDockWidget, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(4)
        
        lbl = QLabel(title)
        lbl.setStyleSheet(f"font-weight: 700; color: {COLORS['text_primary']}; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;")
        layout.addWidget(lbl)
        layout.addStretch()
        
        btn_style = f"""
            QPushButton {{ 
                background: transparent; 
                border: none; 
                border-radius: 4px; 
                color: #FFFFFF; 
                font-weight: bold; 
                font-family: {FONTS['family_ui']};
                font-size: 16px; 
                padding: 4px;
            }}
            QPushButton:hover {{ 
                background: {COLORS['bg_hover']}; 
            }}
        """
        
        float_btn = QPushButton("❐")
        float_btn.setFixedSize(26, 26)
        float_btn.setToolTip("Float / Undock")
        float_btn.setStyleSheet(btn_style)
        float_btn.clicked.connect(lambda: dock.setFloating(not dock.isFloating()))
        layout.addWidget(float_btn)
        
        min_btn = QPushButton("−")
        min_btn.setFixedSize(26, 26)
        min_btn.setToolTip("Minimize (Hide)")
        min_btn.setStyleSheet(btn_style)
        min_btn.clicked.connect(lambda: dock.setVisible(False))
        layout.addWidget(min_btn)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setToolTip("Close panel")
        close_btn.setStyleSheet(btn_style + f"QPushButton:hover {{ background: {COLORS['accent_red']}; color: white; }}")
        close_btn.clicked.connect(lambda: dock.setVisible(False))
        layout.addWidget(close_btn)
        
        # Add a subtle button to restore other panels? No, user said "behind x".
        # I'll just make the x very visible.


from PyQt6.QtWidgets import QCompleter, QScrollArea, QGroupBox
from PyQt6.QtGui import QTextCursor

class PyShaftCodeEditor(QPlainTextEdit):
    """A code editor with basic PyShaft command completion."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(False)
        self.setFont(QFont("Cascadia Code", 11))
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {COLORS['bg_darkest']};
                color: {COLORS['accent_green']};
                border: none;
                padding: 12px;
                font-family: {FONTS['family_mono']};
            }}
        """)
        
        # Setup Completer
        self.completer = QCompleter([
            "click", "double_click", "right_click", "type", "hover", "scroll",
            "select", "check", "uncheck", "submit", "clear", "press",
            "wait_until", "wait_until_disappears",
            "assert_visible", "assert_hidden", "assert_text", "assert_contain_text",
            "assert_enabled", "assert_disabled", "assert_checked",
            "assert_title", "assert_url", "assert_contain_title", "assert_contain_url",
            "assert_data_type", "assert_value", "assert_snapshot",
            "get_text", "get_value", "get_attribute", "get_selected_option",
            "open", "go_back", "go_forward", "refresh", "switch_to_iframe"
        ], self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated.connect(self._insert_completion)

    def _insert_completion(self, completion):
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def text_under_cursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def keyPressEvent(self, event):
        if self.completer and self.completer.popup().isVisible():
            if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                event.ignore()
                return

        # Trigger completer on '.' or after a few characters
        is_shortcut = (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and event.key() == Qt.Key.Key_Space
        super().keyPressEvent(event)

        completion_prefix = self.text_under_cursor()
        if not is_shortcut and (not event.text() or len(completion_prefix) < 2):
            self.completer.popup().hide()
            return

        if completion_prefix != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(completion_prefix)
            self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(self.completer.popup().sizeHintForColumn(0) + self.completer.popup().verticalScrollBar().sizeHint().width())
        self.completer.complete(cr)


class HelpPanel(QWidget):
    """A friendly guide for manual testers."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)
        
        title = QLabel("💡 Quick Guide for Testers")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['accent_purple']}; padding: 5px;")
        content_layout.addWidget(title)
        
        tips = [
            ("🔍 How to start?", "Click the <b>Inspector</b> icon (eyeglass) and then click any element on the webpage to see options."),
            ("⏺ Auto-Recording", "Toggle the <b>Record</b> button to capture your actions (clicks, typing) as you perform them."),
            ("📋 Creating Assertions", "Use the Inspector to click an element, then pick an <b>Assertion</b> (like 'Visible' or 'Text') to verify it."),
            ("⚙️ Locators", "Elements have 'addresses' called Locators. PyShaft finds the most stable one, but you can pick others if needed."),
            ("📝 Editing Code", "The tabs below show your actions as Python code. You can edit them manually; use <b>Ctrl+Space</b> for suggestions!"),
            ("🔀 Workflow", "Check the <b>Workflow</b> tab to see a visual diagram of your test steps.")
        ]
        
        for t_title, t_text in tips:
            group = QGroupBox(t_title)
            group_layout = QVBoxLayout(group)
            lbl = QLabel(t_text)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px;")
            group_layout.addWidget(lbl)
            content_layout.addWidget(group)
            
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)


class MainWindow(QMainWindow):
    """Main recorder window with integrated web view."""

    def __init__(self, parent=None, start_mode: str = "inspect"):
        super().__init__(parent)
        self.setWindowTitle("PyShaft Recorder")
        self.setMinimumSize(1200, 750)
        self.resize(1440, 860)

        # State — set from start_mode ('inspect', 'record', or 'both')
        self._session = RecordingSession(
            name="Untitled Test",
            created_at=time.time(),
        )
        self._browser_bridge = None
        self._is_recording = start_mode in ("record", "both")
        self._is_inspecting = start_mode in ("inspect", "both")
        self._start_mode = start_mode
        self._code_mode = "chain"  # Default to chain style
        self._undo_stack: list[str] = []  # JSON snapshots for undo

        # Build UI
        self._setup_menu_bar()
        self._setup_panels()      # Create panels FIRST
        self._setup_toolbar()     # Then sync toolbar
        self._setup_status_bar()
        self._setup_shortcuts()

        # Initialize WebEngine
        self._setup_web_engine()

        # Element action popup (shown on inspector click)
        self._element_popup = ElementActionPopup()
        self._element_popup.step_requested.connect(self._on_step_from_popup)
        self._element_popup.snapshot_capture_requested.connect(self._on_snapshot_capture_requested)

        # Command palette
        self._command_palette = CommandPalette(self)
        self._command_palette.command_selected.connect(self._on_command_selected)

        # Start with default URL if none provided
        QTimer.singleShot(500, self._start_initial_state)

    def _start_initial_state(self):
        """Start the initial state based on the launch mode."""
        self._url_bar.setText("https://google.com")
        self._on_url_enter()

        # Sync mode combo with start_mode
        mode_map = {"inspect": 0, "record": 1, "both": 2}
        self._mode_combo.setCurrentIndex(mode_map.get(self._start_mode, 0))
        self._update_ui_state()
        self._refresh_code_output()

    def _setup_web_engine(self):
        """Configure the integrated web view."""
        self._web_view.page().console_message.connect(self._on_console_message)
        self._web_view.urlChanged.connect(self._on_web_url_changed)
        self._web_view.loadFinished.connect(self._on_load_finished)

    def _on_console_message(self, level, message, line, source):
        """Handle console messages from the web view."""
        if message.startswith("__PYSHAFT_EVENT__:"):
            try:
                event_data = json.loads(message[len("__PYSHAFT_EVENT__:"):])
                self._handle_browser_event(event_data)
            except json.JSONDecodeError:
                pass
        elif message.startswith("__PYSHAFT_INSPECT__:"):
            try:
                inspect_data = json.loads(message[len("__PYSHAFT_INSPECT__:"):])
                self._handle_browser_event({"type": "inspect", **inspect_data})
            except json.JSONDecodeError:
                pass

    def _on_web_url_changed(self, url: QUrl):
        self._url_bar.setText(url.toString())

    def _on_load_finished(self, ok):
        if ok:
            self._inject_scripts()

    def _inject_scripts(self):
        """Inject recorder/inspector scripts into the integrated web view."""
        js_dir = Path(__file__).parent / "js"
        
        # Always inject inspector if in inspect mode
        if self._is_inspecting:
            inspector_js = (js_dir / "inspector.js").read_text(encoding="utf-8")
            self._web_view.page().runJavaScript(inspector_js)
            
        # Inject recorder if recording
        if self._is_recording:
            recorder_js = (js_dir / "recorder.js").read_text(encoding="utf-8")
            self._web_view.page().runJavaScript(recorder_js)

    # -------------------------------------------------------------------------
    # Menu Bar
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Menu Bar
    # -------------------------------------------------------------------------

    def _setup_menu_bar(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        new_action = file_menu.addAction("New Recording")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_session)

        open_action = file_menu.addAction("Open Recording...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_session)

        file_menu.addSeparator()

        save_action = file_menu.addAction("Save Recording")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save_session)

        save_as_action = file_menu.addAction("Save As...")
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self._on_save_as_session)

        file_menu.addSeparator()

        export_code_action = file_menu.addAction(f"{ICONS['export']}  Export Code (.py)")
        export_code_action.setShortcut("Ctrl+E")
        export_code_action.triggered.connect(self._on_export_code)

        export_session_action = file_menu.addAction("Export Session (.pyshaft)")
        export_session_action.triggered.connect(self._on_export_session)

        file_menu.addSeparator()

        # Recent files submenu
        recent_menu = file_menu.addMenu("Recent Files")
        recent_files = IOManager.get_recent_files(5)
        if recent_files:
            for f in recent_files:
                action = recent_menu.addAction(f.stem)
                action.triggered.connect(partial(self._load_session_file, f))
        else:
            no_recent = recent_menu.addAction("(no recent files)")
            no_recent.setEnabled(False)

        file_menu.addSeparator()
        quit_action = file_menu.addAction("Quit")
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)

        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")

        undo_action = edit_menu.addAction(f"{ICONS['undo']}  Undo")
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self._on_undo)

        edit_menu.addSeparator()

        rename_action = edit_menu.addAction("Rename Test...")
        rename_action.triggered.connect(self._on_rename_test)

        # View menu
        self._view_menu = menu_bar.addMenu("&View")

        toggle_chain = self._view_menu.addAction("Toggle Chain/Flat Code")
        toggle_chain.setShortcut("Ctrl+T")
        toggle_chain.triggered.connect(self._toggle_code_mode)
        
        self._view_menu.addSeparator()

        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")

        cmd_palette = tools_menu.addAction(f"{ICONS['search']}  Command Palette")
        cmd_palette.setShortcut("Ctrl+K")
        cmd_palette.triggered.connect(self._show_command_palette)

    # -------------------------------------------------------------------------
    # Toolbar
    # -------------------------------------------------------------------------

    def _setup_toolbar(self):
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("toolbar_frame")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(6, 2, 6, 2)
        toolbar_layout.setSpacing(4)

        def _add_vsep():
            line = QFrame()
            line.setFrameShape(QFrame.Shape.VLine)
            line.setStyleSheet(f"color: {COLORS['border']};")
            toolbar_layout.addWidget(line)

        # ── Sidebar Toggles (S, I, O) ──────────────────────────────────
        def _add_dock_toggle(dock: QDockWidget, name: str, char: str):
            btn = QToolButton()
            btn.setText(char)
            btn.setCheckable(True)
            btn.setChecked(dock.isVisible())
            btn.setToolTip(f"Show/Hide {name} Panel ({char})")
            dock.visibilityChanged.connect(btn.setChecked)
            def on_click():
                dock.setVisible(btn.isChecked())
                if btn.isChecked(): dock.raise_()
            btn.clicked.connect(on_click)
            btn.setFixedSize(26, 26)
            btn.setStyleSheet(f"""
                QToolButton {{
                    color: white; font-weight: bold; border: 1px solid {COLORS['border']}; border-radius: 4px;
                }}
                QToolButton:checked {{
                    background: {COLORS['accent_purple']}; border-color: white;
                }}
            """)
            toolbar_layout.addWidget(btn)
            return btn

        self._show_steps_btn = _add_dock_toggle(self._left_dock, "Steps", "S")
        self._show_insp_btn = _add_dock_toggle(self._right_dock, "Inspector", "I")
        self._show_out_btn = _add_dock_toggle(self._bottom_dock, "Outputs", "O")
        
        _add_vsep()

        # ── Mode Selector (Condensed) ──────────────────────────────────
        self._mode_combo = QComboBox()
        self._mode_combo.setObjectName("mode_toggle")
        self._mode_combo.addItems(["Insp", "Rec", "Both"])
        self._mode_combo.setFixedWidth(65)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        toolbar_layout.addWidget(self._mode_combo)

        # ── Inspector Toggle (Tool) ───────────────────────────────────
        self._inspect_btn = QPushButton(ICONS['inspect'])
        self._inspect_btn.setCheckable(True)
        self._inspect_btn.setFixedSize(30, 30)
        self._inspect_btn.setToolTip("Toggle Element Picker (Ctrl+I)")
        self._inspect_btn.clicked.connect(self._toggle_inspect)
        self._inspect_btn.setStyleSheet(f"padding: 0; font-size: 16px;")
        toolbar_layout.addWidget(self._inspect_btn)

        # ── Record Controls (Icons Only) ───────────────────────────────
        self._record_btn = QPushButton(ICONS['record'])
        self._record_btn.setObjectName("record_btn")
        self._record_btn.setCheckable(True)
        self._record_btn.setFixedSize(30, 30)
        self._record_btn.setToolTip("Toggle Recording (Ctrl+R)")
        self._record_btn.clicked.connect(self._toggle_recording)
        self._record_btn.setStyleSheet(f"padding: 0; font-size: 18px;")
        toolbar_layout.addWidget(self._record_btn)

        self._pause_btn = QPushButton(ICONS['pause'])
        self._pause_btn.setEnabled(False)
        self._pause_btn.setCheckable(True)
        self._pause_btn.setFixedSize(30, 30)
        self._pause_btn.setToolTip("Pause/Resume")
        self._pause_btn.clicked.connect(self._toggle_pause)
        self._pause_btn.setStyleSheet(f"padding: 0; font-size: 16px;")
        toolbar_layout.addWidget(self._pause_btn)

        self._stop_btn = QPushButton(ICONS['stop'])
        self._stop_btn.setEnabled(False)
        self._stop_btn.setFixedSize(30, 30)
        self._stop_btn.setToolTip("Stop Recording")
        self._stop_btn.clicked.connect(self._stop_recording)
        self._stop_btn.setStyleSheet(f"padding: 0; font-size: 16px;")
        toolbar_layout.addWidget(self._stop_btn)

        _add_vsep()

        # Helpers
        self._zen_btn = QPushButton("Zen")
        self._zen_btn.setCheckable(True)
        self._zen_btn.setFixedSize(36, 28)
        self._zen_btn.clicked.connect(self._toggle_zen_mode)
        toolbar_layout.addWidget(self._zen_btn)
        
        restore_btn = QPushButton("↺")
        restore_btn.setToolTip("Restore All Panels")
        restore_btn.setFixedSize(28, 28)
        restore_btn.clicked.connect(self._restore_layout)
        toolbar_layout.addWidget(restore_btn)

        _add_vsep()

        # ── Navigation / Session ──────────────────────────────────────
        self._url_bar = QLineEdit()
        self._url_bar.setPlaceholderText("Enter URL...")
        self._url_bar.setStyleSheet(f"background: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 2px 6px;")
        self._url_bar.returnPressed.connect(self._on_url_enter)
        toolbar_layout.addWidget(self._url_bar, 2)
        
        go_btn = QPushButton("Go")
        go_btn.setObjectName("primary")
        go_btn.setFixedSize(32, 28)
        go_btn.clicked.connect(self._on_url_enter)
        toolbar_layout.addWidget(go_btn)
        
        self._name_input = QLineEdit(self._session.name)
        self._name_input.setPlaceholderText("Test File")
        self._name_input.setFixedWidth(100)
        self._name_input.setStyleSheet(f"background: {COLORS['bg_darkest']}; border: 1px solid {COLORS['accent_purple']}; border-radius: 4px; padding: 2px 6px;")
        self._name_input.textChanged.connect(self._on_name_changed)
        toolbar_layout.addWidget(self._name_input)

        # Final setup
        self._toolbar_frame = toolbar_frame
        from PyQt6.QtWidgets import QToolBar
        self._main_toolbar = QToolBar("Main Toolbar")
        self._main_toolbar.setMovable(False)
        self._main_toolbar.addWidget(self._toolbar_frame)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._main_toolbar)

    # -------------------------------------------------------------------------
    # Main Panels
    # -------------------------------------------------------------------------

    def _setup_panels(self):
        from PyQt6.QtWidgets import QDockWidget
        
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Center panel — Integrated Web View
        self._web_view = QWebEngineView()
        self._web_view.setPage(RecorderWebPage(self._web_view))
        self._web_view.setMinimumWidth(600)

        # Left panel — Step List Dock
        self._step_list = StepListPanel()
        self._step_list.setMinimumWidth(240)
        self._step_list.step_deleted.connect(self._on_step_deleted)
        self._step_list.step_edited.connect(self._on_step_edit)
        self._step_list.step_duplicated.connect(self._on_step_duplicated)
        self._step_list.step_selected.connect(self._on_step_selected)
        self._step_list.set_session(self._session)
        
        self._left_dock = QDockWidget("Steps", self)
        self._left_dock.setObjectName("steps_dock")
        self._left_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self._left_dock.setWidget(self._step_list)
        self._left_dock.setTitleBarWidget(DockTitleBar("Steps", self._left_dock))
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._left_dock)

        # Right panel — Inspector Dock
        self._inspector = InspectorPanel()
        self._inspector.setMinimumWidth(280)
        self._inspector.step_requested.connect(self._on_step_from_inspector)
        self._inspector.snapshot_capture_requested.connect(self._on_snapshot_capture_requested)

        self._right_dock = QDockWidget("Inspector", self)
        self._right_dock.setObjectName("inspector_dock")
        self._right_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self._right_dock.setWidget(self._inspector)
        self._right_dock.setTitleBarWidget(DockTitleBar("Inspector", self._right_dock))
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._right_dock)

        # Bottom panel — Tabbed output
        bottom_tabs = QTabWidget()
        bottom_tabs.setMinimumHeight(200)

        # Basic Code tab
        def create_code_editor_with_copy(title: str = ""):
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # Mini header for the editor
            header = QFrame()
            header.setStyleSheet(f"background: {COLORS['bg_dark']}; border-bottom: 1px solid {COLORS['border']};")
            h_layout = QHBoxLayout(header)
            h_layout.setContentsMargins(8, 4, 8, 4)
            
            if title:
                lbl = QLabel(title)
                lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: bold;")
                h_layout.addWidget(lbl)
            
            h_layout.addStretch()
            
            copy_btn = QPushButton(f"{ICONS.get('copy', '📋')} Copy")
            copy_btn.setFixedSize(65, 22)
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 10px; padding: 0; background: {COLORS['bg_card']}; border: 1px solid {COLORS['border']};
                }}
                QPushButton:hover {{ background: {COLORS['bg_hover']}; }}
            """)
            h_layout.addWidget(copy_btn)

            editor = PyShaftCodeEditor()
            
            layout.addWidget(header)
            layout.addWidget(editor)
            
            copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(editor.toPlainText()))
            
            return container, editor

        self._code_container, self._code_output = create_code_editor_with_copy()
        bottom_tabs.addTab(self._code_container, f"{ICONS['code']}  Code")
        
        # POM Tab container
        self._pom_tab_widget = QTabWidget()
        self._test_container, self._test_output = create_code_editor_with_copy("TEST")
        self._page_container, self._page_output = create_code_editor_with_copy("PAGE")
        self._data_container, self._data_output = create_code_editor_with_copy("DATA")

        self._pom_tab_widget.addTab(self._test_container, "test.py")
        self._pom_tab_widget.addTab(self._page_container, "page.py")
        self._pom_tab_widget.addTab(self._data_container, "data.py")
        
        bottom_tabs.addTab(self._pom_tab_widget, "📦  POM")

        # Guide Tab for manual testers
        self._help_panel = HelpPanel()
        bottom_tabs.addTab(self._help_panel, "💡  Guide")

        # Code mode toggle for the basic Code tab
        self._code_mode_combo = QComboBox()
        self._code_mode_combo.addItems([
            "Flat (one line per action)", 
            "Chain (fluent chaining)",
        ])
        self._code_mode_combo.setCurrentIndex(1) # Chain by default
        self._code_mode_combo.currentIndexChanged.connect(self._on_code_mode_changed)
        # Add as corner widget
        bottom_tabs.setCornerWidget(self._code_mode_combo, Qt.Corner.TopRightCorner)

        # Workflow tab
        self._workflow_view = WorkflowView()
        self._workflow_view.step_removed.connect(self._on_step_deleted)
        self._workflow_view.step_edited.connect(self._on_step_edit)
        bottom_tabs.addTab(self._workflow_view, f"{ICONS['workflow']}  Workflow")

        main_layout.addWidget(self._web_view)
        self.setCentralWidget(central)

        self._bottom_dock = QDockWidget("Outputs", self)
        self._bottom_dock.setObjectName("bottom_dock")
        self._bottom_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea)
        self._bottom_dock.setWidget(bottom_tabs)
        self._bottom_dock.setTitleBarWidget(DockTitleBar("Outputs", self._bottom_dock))
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._bottom_dock)
        
        # Add dock toggles to View menu
        self._view_menu.addAction(self._left_dock.toggleViewAction())
        self._view_menu.addAction(self._right_dock.toggleViewAction())
        self._view_menu.addAction(self._bottom_dock.toggleViewAction())

    # -------------------------------------------------------------------------
    # Status Bar
    # -------------------------------------------------------------------------

    def _setup_status_bar(self):
        status = self.statusBar()
        status.setStyleSheet(f"""
            QStatusBar {{
                background-color: {COLORS['bg_darkest']};
                border-top: 1px solid {COLORS['border']};
                color: {COLORS['text_secondary']};
            }}
            QStatusBar::item {{ border: none; }}
        """)
        
        self._status_bar_label = QLabel("  Ready")
        self._status_bar_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 500;")
        status.addWidget(self._status_bar_label)

        self._step_count_label = QLabel(" 0 steps  ")
        self._step_count_label.setStyleSheet(f"""
            color: {COLORS['accent_purple']}; 
            font-weight: bold; 
            background-color: {COLORS['bg_dark']};
            border-left: 1px solid {COLORS['border']};
            padding: 0 10px;
        """)
        status.addPermanentWidget(self._step_count_label)


    # -------------------------------------------------------------------------
    # Keyboard Shortcuts
    # -------------------------------------------------------------------------

    def _setup_shortcuts(self):
        """Register global keyboard shortcuts."""
        # Ctrl+R — Toggle recording
        rec_shortcut = QAction("Record", self)
        rec_shortcut.setShortcut(QKeySequence("Ctrl+R"))
        rec_shortcut.triggered.connect(self._toggle_recording)
        self.addAction(rec_shortcut)

        # Ctrl+I — Toggle inspect
        inspect_shortcut = QAction("Inspect", self)
        inspect_shortcut.setShortcut(QKeySequence("Ctrl+I"))
        inspect_shortcut.triggered.connect(self._toggle_inspect)
        self.addAction(inspect_shortcut)

        # Ctrl+K — Command Palette
        cmd_shortcut = QAction("Command Palette", self)
        cmd_shortcut.setShortcut(QKeySequence("Ctrl+K"))
        cmd_shortcut.triggered.connect(self._show_command_palette)
        self.addAction(cmd_shortcut)

        # Ctrl+Z — Undo
        undo_shortcut = QAction("Undo", self)
        undo_shortcut.setShortcut(QKeySequence("Ctrl+Z"))
        undo_shortcut.triggered.connect(self._on_undo)
        self.addAction(undo_shortcut)

    def _on_mode_changed(self, index: int):
        """Handle mode combo change: 0=Inspector, 1=Record, 2=Both."""
        if index == 0:  # Inspector
            self._is_inspecting = True
            if self._is_recording:
                self._stop_recording()
        elif index == 1:  # Record
            self._is_inspecting = False
            if not self._is_recording:
                self._start_recording()
        elif index == 2:  # Both
            self._is_inspecting = True
            if not self._is_recording:
                self._start_recording()
        self._update_ui_state()

    def _update_ui_state(self):
        """Update UI elements based on current recording/inspecting state."""
        self._record_btn.setChecked(self._is_recording)
        self._inspect_btn.setChecked(self._is_inspecting)

        # Highlight Record Button
        if self._is_recording:
            self._pause_btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
            self._status_bar_label.setText("⏺  Recording in progress")
            self._record_btn.setStyleSheet(f"background: {COLORS['accent_red']}; color: white; border-radius: 15px; padding: 0; font-size: 18px;")
        else:
            self._pause_btn.setEnabled(False)
            self._stop_btn.setEnabled(False)
            self._record_btn.setStyleSheet(f"padding: 0; font-size: 18px;")

        # Highlight Inspect Button
        if self._is_inspecting:
            self._inspect_btn.setStyleSheet(f"background: {COLORS['accent_purple']}; color: white; border-radius: 15px; padding: 0; font-size: 16px;")
            if not self._is_recording:
                self._status_bar_label.setText("🔍  Inspector active — click elements to inspect")
        else:
            self._inspect_btn.setStyleSheet(f"padding: 0; font-size: 16px;")
            if not self._is_recording:
                self._status_bar_label.setText("Ready")

        if self._is_inspecting and self._is_recording:
            self._status_bar_label.setText("🔍+⏺  Inspector + Recording active")

        self._inject_scripts()

    # -------------------------------------------------------------------------
    # Recording Controls
    # -------------------------------------------------------------------------

    def _restore_layout(self):
        """Force all docks to be visible and reset Zen mode."""
        self._is_zen = False
        self._zen_btn.setChecked(False)
        self._left_dock.show()
        self._left_dock.setFloating(False)
        self._right_dock.show()
        self._right_dock.setFloating(False)
        self._bottom_dock.show()
        self._bottom_dock.setFloating(False)
        self._status_bar_label.setText("Layout Restored")

    def _toggle_recording(self):
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        url = self._url_bar.text().strip()
        if not url:
            url = "https://google.com"
        if not url.startswith(("http://", "https://", "about:")):
            url = "https://" + url

        # Save undo state
        self._push_undo()

        if self._web_view.url().isEmpty() or self._web_view.url().toString() == "about:blank":
            self._web_view.setUrl(QUrl(url))

        # Add open_url step if session is new
        if not self._session.steps:
            step = RecordedStep(
                action="open_url",
                locator_value=url,
                url=url,
                timestamp=time.time(),
            )
            self._session.start_url = url
            self._step_list.add_step(step)

        self._is_recording = True
        self._update_ui_state()

    def _stop_recording(self):
        self._is_recording = False
        self._update_ui_state()
        self._refresh_all()

    def _toggle_pause(self):
        # In-page pause via JS
        if self._pause_btn.isChecked():
            self._web_view.page().runJavaScript("if(window.__pyshaft_recorder) window.__pyshaft_recorder.pause();")
            self._status_bar_label.setText("Recording paused")
        else:
            self._web_view.page().runJavaScript("if(window.__pyshaft_recorder) window.__pyshaft_recorder.resume();")
            self._status_bar_label.setText("Recording in progress")

    # -------------------------------------------------------------------------
    # Inspect Controls
    # -------------------------------------------------------------------------

    def _toggle_inspect(self):
        self._is_inspecting = not self._is_inspecting
        self._update_ui_state()

    def _start_inspect(self):
        self._is_inspecting = True
        self._update_ui_state()

    def _stop_inspect(self):
        self._is_inspecting = False
        self._web_view.page().runJavaScript("if (window.__pyshaft_inspector) window.__pyshaft_inspector.stop();")
        self._update_ui_state()

    def _toggle_zen_mode(self):
        is_zen = self._zen_btn.isChecked()
        self._left_dock.setVisible(not is_zen)
        self._right_dock.setVisible(not is_zen)
        self._bottom_dock.setVisible(not is_zen)

    # -------------------------------------------------------------------------
    # Browser Event Handlers
    # -------------------------------------------------------------------------

    def _on_snapshot_capture_requested(self, name: str, meta: dict):
        """Take a screenshot of the element and save as baseline."""
        rect_data = meta.get("rect", {})
        if not rect_data:
            return
            
        # Element rect in viewport
        rx = rect_data.get("x", 0)
        ry = rect_data.get("y", 0)
        rw = rect_data.get("width", 100)
        rh = rect_data.get("height", 100)
        
        # Grab from web view widget
        # Note: We use a small delay to ensure any highlight is gone, 
        # but the popup call is already after the event.
        pixmap = self._web_view.grab(QRect(rx, ry, rw, rh))
        
        # Save to saved_snapshots
        base_dir = Path("saved_snapshots")
        base_dir.mkdir(exist_ok=True)
        path = base_dir / f"{name}.png"
        
        if pixmap.save(str(path), "PNG"):
             self._status_bar_label.setText(f"  📸 Captured baseline: {name}.png")
        else:
             logger.error("Failed to save snapshot: %s", path)

    def _handle_browser_event(self, event: dict):
        """Process browser event on the main thread."""
        event_type = event.get("type", "")

        if event_type == "recorder_ready":
            logger.info("Recorder JS ready on %s", event.get("url"))
            return

        if event_type == "inspect":
            # Inspector click — update inspector panel AND show popup
            element = event.get("element", {})
            locators_data = event.get("locators", [])
            suggestions = [
                LocatorSuggestion(
                    locator_type=loc.get("type", ""),
                    value=loc.get("value", ""),
                    modifier=loc.get("modifier"),
                    stability=loc.get("stability", "medium"),
                    score=loc.get("score", 50),
                )
                for loc in locators_data
            ]
            # Sync the right-sidebar inspector
            self._inspector.set_element(element, suggestions)

            # Show the rich floating popup at cursor position
            self._element_popup.show_for_element(element, suggestions)

            # Stop inspect mode so it doesn't keep highlighting (eyedropper behavior)
            self._stop_inspect()
            return

        # Recording events — only process if recording is active
        if not self._is_recording:
            return

        element = event.get("element", {})
        locators_data = event.get("locators", [])

        # Pick the best locator
        best_locator = None
        for loc in sorted(locators_data, key=lambda l: l.get("score", 0), reverse=True):
            if loc.get("value"):
                best_locator = loc
                break

        step = RecordedStep(
            action=event_type,
            locator_type=best_locator.get("type") if best_locator else None,
            locator_value=best_locator.get("value", "") if best_locator else "",
            modifier=best_locator.get("modifier") if best_locator else None,
            timestamp=time.time(),
            url=element.get("url", ""),
            element_meta=element,
        )

        # Handle type events — capture the typed text
        if event_type == "type":
            step.typed_text = event.get("value", "")

        # Handle select events
        if event_type == "select":
            step.typed_text = event.get("selectedOption", event.get("selectedValue", ""))

        self._push_undo()
        self._step_list.add_step(step)
        self._refresh_all()

    def _on_browser_navigate(self, url: str):
        """Handle page navigation in the browser."""
        self._url_bar.setText(url)

    # -------------------------------------------------------------------------
    # Inspector → Step
    # -------------------------------------------------------------------------

    def _on_step_from_inspector(self, step: RecordedStep):
        """Handle a step created from the inspector panel."""
        self._push_undo()
        self._step_list.add_step(step)
        self._refresh_all()

    def _on_step_from_popup(self, step: RecordedStep):
        """Handle a step created from the element action popup."""
        # Check if we need more info for specific actions
        if step.action == "upload":
            path, _ = QFileDialog.getOpenFileName(self, "Select File to Upload")
            if not path: return
            step.typed_text = path
            step.action = "upload_file"
        elif step.action == "pick_date":
            if not step.typed_text:
                date, ok = QInputDialog.getText(self, "Pick Date", "Enter date (e.g. 2023-12-25):")
                if not (ok and date): return
                step.typed_text = date
        elif step.action == "type":
            if not step.typed_text:
                text, ok = QInputDialog.getText(self, "Type Text", "Enter text to type:")
                if not (ok and text): return
                step.typed_text = text
        elif step.action == "select":
            if not step.typed_text:
                opt, ok = QInputDialog.getText(
                    self, "Select Option", "Enter option text, value, or index:"
                )
                if not (ok and opt): return
                step.typed_text = opt
        elif step.action == "assert_snapshot":
            pass # Handled in popup
        elif step.action == "assert_text" or step.action == "assert_contain_text":
            if not step.assert_expected:
                expected, ok = QInputDialog.getText(self, "Assert Text", "Expected text:")
                if not (ok and expected): return
                step.assert_expected = expected
        elif step.action == "wait_disappear":
            step.action = "wait_until_disappears"

        self._push_undo()
        self._step_list.add_step(step)
        self._refresh_all()

    # -------------------------------------------------------------------------
    # Step Management
    # -------------------------------------------------------------------------

    def _on_step_deleted(self, step_id: str):
        self._push_undo()
        self._session.remove_step(step_id)
        self._step_list.refresh()
        self._refresh_all()

    def _on_step_edit(self, step_id: str):
        step = self._session.get_step(step_id)
        if not step:
            return

        from pyshaft.recorder.step_editor_dialog import StepEditorDialog
        dialog = StepEditorDialog(step, self)
        if dialog.exec():
            result = dialog.get_result()
            if result:
                self._push_undo()
                # Replace step in session
                for i, s in enumerate(self._session.steps):
                    if s.id == step_id:
                        self._session.steps[i] = result
                        break
                self._step_list.refresh()
                self._refresh_all()

    def _on_step_duplicated(self, step_id: str):
        self._push_undo()
        self._session.duplicate_step(step_id)
        self._step_list.refresh()
        self._refresh_all()

    def _on_step_selected(self, step_id: str):
        step = self._session.get_step(step_id)
        if step and step.element_meta:
            locators_data = step.element_meta.get("locators", [])
            suggestions = []
            if step.locator_type and step.locator_value:
                suggestions.append(LocatorSuggestion(
                    locator_type=step.locator_type,
                    value=step.locator_value,
                    modifier=step.modifier,
                    stability="high",
                    score=100,
                ))
            self._inspector.set_element(step.element_meta, suggestions)

    # -------------------------------------------------------------------------
    # URL Navigation
    # -------------------------------------------------------------------------

    def _on_url_enter(self):
        url = self._url_bar.text().strip()
        if not url:
            return
        if not url.startswith(("http://", "https://", "about:")):
            url = "https://" + url
            self._url_bar.setText(url)

        self._web_view.setUrl(QUrl(url))
        if not self._is_recording and not self._is_inspecting:
            self._start_inspect()

    # -------------------------------------------------------------------------
    # Code Output
    # -------------------------------------------------------------------------

    def _refresh_code_output(self):
        """Refresh the code preview panel."""
        if not self._session.steps:
            self._code_output.setPlainText("# Start recording to generate code...")
            self._test_output.setPlainText("# Start recording to generate code...")
            self._page_output.setPlainText("# Start recording to generate code...")
            self._data_output.setPlainText("# Start recording to generate code...")
            self._step_count_label.setText("0 steps")
            return

        try:
            # Refresh Basic Code
            code = generate_code(self._session, mode=self._code_mode)
            self._code_output.setPlainText(code)

            # Refresh POM
            pom_code = generate_code(self._session, mode="pom")
            self._test_output.setPlainText(pom_code.get("test.py", ""))
            self._page_output.setPlainText(pom_code.get("page.py", ""))
            self._data_output.setPlainText(pom_code.get("data.py", ""))
        except Exception as e:
            self._code_output.setPlainText(f"# Error generating code: {e}")
            self._test_output.setPlainText(f"# Error generating pom: {e}")

        self._step_count_label.setText(f"{len(self._session.steps)} steps")

    def _refresh_all(self):
        """Refresh all output panels."""
        self._refresh_code_output()

        # Refresh workflow
        self._workflow_view.build_from_session(self._session)

    def _on_code_mode_changed(self, index: int):
        self._code_mode = "chain" if index == 1 else "flat"
        self._refresh_code_output()

    def _toggle_code_mode(self):
        current = self._code_mode_combo.currentIndex()
        self._code_mode_combo.setCurrentIndex(1 - current)

    # -------------------------------------------------------------------------
    # File Operations
    # -------------------------------------------------------------------------

    def _on_new_session(self):
        self._session = RecordingSession(
            name="Untitled Test",
            created_at=time.time(),
        )
        self._name_input.setText(self._session.name)
        self._step_list.set_session(self._session)
        self._refresh_all()
        self._undo_stack.clear()

    def _on_open_session(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Recording",
            str(IOManager.get_recordings_dir()),
            "PyShaft Sessions (*.pyshaft);;All Files (*)",
        )
        if path:
            self._load_session_file(path)

    def _load_session_file(self, path):
        try:
            self._session = IOManager.load_session(path)
            self._name_input.setText(self._session.name)
            self._step_list.set_session(self._session)
            self._refresh_all()
            self._undo_stack.clear()
            self._status_bar_label.setText(f"Loaded: {path}")
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load session:\n{e}")

    def _on_save_session(self):
        try:
            path = IOManager.save_session(self._session)
            self._status_bar_label.setText(f"Saved: {path}")
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save:\n{e}")

    def _on_save_as_session(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Recording As",
            str(IOManager.get_recordings_dir() / f"{self._session.name}.pyshaft"),
            "PyShaft Sessions (*.pyshaft);;All Files (*)",
        )
        if path:
            IOManager.save_session(self._session, path)
            self._status_bar_label.setText(f"Saved: {path}")

    def _on_export_code(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Code",
            f"test_{self._session.name.lower().replace(' ', '_')}.py",
            "Python Files (*.py);;All Files (*)",
        )
        if path:
            IOManager.export_code(self._session, path, mode=self._code_mode)
            self._status_bar_label.setText(f"Code exported: {path}")

    def _on_export_session(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Session",
            f"{self._session.name}.pyshaft",
            "PyShaft Sessions (*.pyshaft);;All Files (*)",
        )
        if path:
            IOManager.save_session(self._session, path)
            self._status_bar_label.setText(f"Session exported: {path}")

    # -------------------------------------------------------------------------
    # Undo
    # -------------------------------------------------------------------------

    def _push_undo(self):
        """Save current state to undo stack."""
        self._undo_stack.append(self._session.to_json())
        # Limit stack size
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)

    def _on_undo(self):
        if not self._undo_stack:
            return
        json_str = self._undo_stack.pop()
        self._session = RecordingSession.from_json(json_str)
        self._name_input.setText(self._session.name)
        self._step_list.set_session(self._session)
        self._refresh_all()

    # -------------------------------------------------------------------------
    # Misc
    # -------------------------------------------------------------------------

    def _on_name_changed(self, text: str):
        self._session.name = text

    def _on_rename_test(self):
        name, ok = QInputDialog.getText(
            self, "Rename Test", "Test name:",
            text=self._session.name,
        )
        if ok and name:
            self._session.name = name
            self._name_input.setText(name)

    def _show_command_palette(self):
        self._command_palette.move(
            self.geometry().center().x() - 240,
            self.geometry().top() + 100,
        )
        self._command_palette.show()

    def _on_command_selected(self, cmd_id: str):
        """Handle command palette selection."""
        if cmd_id == "_record":
            self._toggle_recording()
        elif cmd_id == "_stop":
            self._stop_recording()
        elif cmd_id == "_inspect":
            self._toggle_inspect()
        elif cmd_id == "_export":
            self._on_export_code()
        elif cmd_id == "_undo":
            self._on_undo()
        elif cmd_id == "open_url":
            url, ok = QInputDialog.getText(self, "Open URL", "URL:")
            if ok and url:
                step = RecordedStep(action="open_url", locator_value=url, url=url, timestamp=time.time())
                self._step_list.add_step(step)
                self._refresh_all()
        else:
            # It's an action/assertion — add a step stub
            step = RecordedStep(action=cmd_id, timestamp=time.time())
            # Open step editor for it
            from pyshaft.recorder.step_editor_dialog import StepEditorDialog
            dialog = StepEditorDialog(step, self)
            if dialog.exec():
                result = dialog.get_result()
                if result:
                    self._step_list.add_step(result)
                    self._refresh_all()

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def closeEvent(self, event):
        """Clean up browser on close."""
        if self._browser_bridge:
            self._browser_bridge.close()

        # Auto-save
        if self._session.steps:
            try:
                IOManager.save_session(
                    self._session,
                    IOManager.get_auto_save_path(self._session.name),
                )
            except Exception:
                pass

        super().closeEvent(event)
