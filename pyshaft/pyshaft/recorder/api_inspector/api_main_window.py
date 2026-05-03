"""PyShaft API Inspector — Main window with dockable, tabbed UI.

This is the production-ready upgrade featuring:
- Dockable panels for Explorer, Code, Diagram, Responses, and History.
- Tabbed request builder for working on multiple endpoints.
- Hierarchical collection explorer with search.
- Interactive workflow map.
- Syntax highlighting and Request History.
- Full Variable & Environment Manager.
- Global Search and Keyboard Shortcuts.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import string
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
)

from pyshaft.recorder.api_inspector.api_assertion_panel import (
    ApiAssertionForm,
    ApiExtractionForm,
    ApiPipelineForm,
)
from pyshaft.recorder.api_inspector.api_code_dock import ApiCodeDock
from pyshaft.recorder.api_inspector.api_diagram import ApiDiagramDock
from pyshaft.recorder.api_inspector.api_explorer import ApiExplorerDock
from pyshaft.recorder.api_inspector.api_history import ApiHistoryDock
from pyshaft.recorder.api_inspector.api_io_manager import load_workflow, save_workflow
from pyshaft.recorder.api_inspector.api_json_viewer import ApiJsonViewer
from pyshaft.recorder.api_inspector.api_models import (
    ApiAssertion,
    ApiEnvironment,
    ApiExtraction,
    ApiFolder,
    ApiRequestStep,
    ApiWorkflow,
    AuthType,
    HttpMethod,
    PipelineStep,
)
from pyshaft.recorder.api_inspector.api_request_builder import ApiRequestBuilder
from pyshaft.recorder.api_inspector.api_variable_manager import ApiVariableManager
from pyshaft.recorder.api_inspector.api_search import ApiSearchDialog
from pyshaft.recorder.theme import COLORS, FONTS

logger = logging.getLogger("pyshaft.recorder.api_inspector")


class DockTitleBar(QWidget):
    """Custom title bar for dock widgets with a minimize (hide) button."""
    def __init__(self, dock: QDockWidget, title: str) -> None:
        super().__init__(dock)
        self.dock = dock
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4); layout.setSpacing(4)
        
        self.label = QLabel(title.upper())
        self.label.setStyleSheet(f"font-weight: 700; font-size: 8pt; color: {COLORS['text_secondary']}; letter-spacing: 1px;")
        layout.addWidget(self.label, 1)
        
        btn_style = f"QPushButton {{ background: transparent; border: none; color: {COLORS['text_primary']}; font-size: 14px; border-radius: 3px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS['bg_hover']}; color: {COLORS['accent_purple']}; }}"
        
        btn_min = QPushButton("—")
        btn_min.setFixedSize(24, 20)
        btn_min.setToolTip("Minimize (Hide)")
        btn_min.setStyleSheet(btn_style)
        btn_min.clicked.connect(lambda: self.dock.hide())
        layout.addWidget(btn_min)
        
        btn_float = QPushButton("❐")
        btn_float.setFixedSize(24, 20)
        btn_float.setToolTip("Float/Dock")
        btn_float.setStyleSheet(btn_style)
        btn_float.clicked.connect(lambda: self.dock.setFloating(not self.dock.isFloating()))
        layout.addWidget(btn_float)
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 20)
        btn_close.setToolTip("Close")
        btn_close.setStyleSheet(btn_style)
        btn_close.clicked.connect(lambda: self.dock.close())
        layout.addWidget(btn_close)
        
        self.setStyleSheet(f"background: {COLORS['bg_dark']}; border-bottom: 1px solid {COLORS['border']};")


class _SignalBridge(QObject):
    """Thread-safe bridge for emitting signals from worker threads."""
    response_received = pyqtSignal(int, object, float, str, object)


class ApiMainWindow(QMainWindow):
    """Main API Inspector window using a dockable architecture."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._workflow = ApiWorkflow(); self._bridge = _SignalBridge(); self._bridge.response_received.connect(self._on_response_received)
        self._docks: list[QDockWidget] = []; self._focus_mode = False; self._session_path = Path.home() / ".pyshaft_api_session.json"
        self._current_scope = None  # ApiRequestStep | ApiFolder | None
        import requests; self._session = requests.Session()
        self.setWindowTitle("⚡ PyShaft API Inspector"); self.setMinimumSize(1000, 700)
        
        self._build_central_tabs()
        self._build_docks()
        self._build_menu()
        self._build_toolbar()
        self._build_statusbar()
        self._setup_shortcuts()
        
        # Load last session
        self._load_last_session()
        self._refresh_explorer()

    def closeEvent(self, event) -> None:
        self._save_last_session()
        super().closeEvent(event)

    def _save_last_session(self) -> None:
        try: save_workflow(self._workflow, self._session_path)
        except: pass

    def _load_last_session(self) -> None:
        if self._session_path.exists():
            try: self._workflow = load_workflow(self._session_path)
            except: pass

    def _add_dock(self, dock: QDockWidget, area: Qt.DockWidgetArea, title: str) -> None:
        dock.setTitleBarWidget(DockTitleBar(dock, title))
        dock.setObjectName(title.lower().replace(" ", "_"))
        self.addDockWidget(area, dock)
        self._docks.append(dock)

    def _build_central_tabs(self) -> None:
        from PyQt6.QtWidgets import QSplitter, QFrame
        
        # ── Request Side ──
        req_container = QWidget()
        req_layout = QVBoxLayout(req_container)
        req_layout.setContentsMargins(0, 0, 0, 0); req_layout.setSpacing(0)
        
        req_header = QFrame()
        req_header.setStyleSheet(f"background: {COLORS['bg_dark']}; border-bottom: 1px solid {COLORS['border']};")
        req_h_layout = QHBoxLayout(req_header)
        req_h_layout.setContentsMargins(16, 10, 16, 10)
        req_label = QLabel("REQUEST")
        req_label.setStyleSheet(f"font-weight: 800; font-size: 8pt; color: {COLORS['text_muted']}; letter-spacing: 1.5px;")
        req_h_layout.addWidget(req_label)
        req_h_layout.addStretch()
        req_layout.addWidget(req_header)

        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True); self._tabs.setMovable(True)
        self._tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._tabs.setStyleSheet(f"QTabWidget::pane {{ border: none; background: {COLORS['bg_dark']}; }} QTabBar::tab {{ background: {COLORS['bg_dark']}; padding: 10px 20px; color: {COLORS['text_muted']}; font-size: 11px; }} QTabBar::tab:selected {{ background: {COLORS['bg_card']}; color: {COLORS['accent_purple']}; font-weight: 600; }}")
        req_layout.addWidget(self._tabs)

        # ── Response Side ──
        resp_container = QWidget()
        resp_layout = QVBoxLayout(resp_container)
        resp_layout.setContentsMargins(0, 0, 0, 0); resp_layout.setSpacing(0)
        
        resp_header = QFrame()
        resp_header.setStyleSheet(f"background: {COLORS['bg_dark']}; border-bottom: 1px solid {COLORS['border']};")
        resp_h_layout = QHBoxLayout(resp_header)
        resp_h_layout.setContentsMargins(16, 10, 16, 10)
        resp_label = QLabel("RESPONSE")
        resp_label.setStyleSheet(f"font-weight: 800; font-size: 8pt; color: {COLORS['text_muted']}; letter-spacing: 1.5px;")
        resp_h_layout.addWidget(resp_label)
        resp_h_layout.addStretch()
        
        # Response Metadata Labels
        self._resp_status_label = QLabel("")
        self._resp_status_label.setStyleSheet("font-weight: 700; font-size: 9pt;")
        resp_h_layout.addWidget(self._resp_status_label)
        
        self._resp_time_label = QLabel("")
        self._resp_time_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9pt; margin-left: 8px;")
        resp_h_layout.addWidget(self._resp_time_label)
        
        resp_layout.addWidget(resp_header)

        self._response_viewer = ApiJsonViewer()
        self._response_viewer.assertion_requested.connect(self._on_quick_assertion)
        self._response_viewer.extraction_requested.connect(self._on_quick_extraction)
        self._response_viewer.remove_assertion_requested.connect(self._on_quick_remove_assertion)
        self._response_viewer.path_selected.connect(self._on_json_path_selected)
        self._response_viewer.data_changed.connect(self._on_response_data_edited)
        self._response_viewer.schema_assertion_requested.connect(self._on_schema_assertion)
        resp_layout.addWidget(self._response_viewer)

        # Create a splitter for request/response
        self._splitter = QSplitter()
        self._splitter.setOrientation(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(2)
        self._splitter.addWidget(req_container)
        self._splitter.addWidget(resp_container)
        self._splitter.setSizes([500, 500])
        
        # Main Central Tabs (Centralizing all major views)
        self._main_tabs = QTabWidget()
        self._main_tabs.setStyleSheet(f"QTabWidget::pane {{ border: none; background: {COLORS['bg_dark']}; }} QTabBar::tab {{ background: {COLORS['bg_dark']}; padding: 12px 24px; color: {COLORS['text_muted']}; font-size: 12px; }} QTabBar::tab:selected {{ background: {COLORS['bg_card']}; color: {COLORS['accent_purple']}; font-weight: 700; }}")
        self._main_tabs.addTab(self._splitter, "🛠 Builder")
        
        self.setCentralWidget(self._main_tabs)

    def _build_docks(self) -> None:
        self.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks | QMainWindow.DockOption.AnimatedDocks)
        # 1. Explorer (Left Side)
        self._explorer_dock = ApiExplorerDock(self)
        self._explorer_dock.step_selected.connect(self._open_step_in_tab)
        self._explorer_dock.context_selected.connect(self._on_context_selected)
        self._explorer_dock.item_deleted.connect(self._on_item_deleted_refresh)
        self._explorer_dock.export_docs_requested.connect(self._export_html_docs)
        self._add_dock(self._explorer_dock, Qt.DockWidgetArea.LeftDockWidgetArea, "Explorer")
        
        # 2. Assertions, Extractions, Pipeline (Right Side)
        self._assert_form = ApiAssertionForm(); self._assert_form.added.connect(self._on_assertion_added); self._assert_form.deleted.connect(self._on_assertion_deleted); self._assert_form.edited.connect(self._on_assertion_edited); self._assert_dock = QDockWidget("Assertions", self); self._assert_dock.setWidget(self._assert_form); self._add_dock(self._assert_dock, Qt.DockWidgetArea.RightDockWidgetArea, "Assertions")
        self._extract_form = ApiExtractionForm(); self._extract_form.added.connect(self._on_extraction_added); self._extract_form.deleted.connect(self._on_extraction_deleted); self._extract_form.edited.connect(self._on_extraction_edited); self._extract_dock = QDockWidget("Extractions", self); self._extract_dock.setWidget(self._extract_form); self._add_dock(self._extract_dock, Qt.DockWidgetArea.RightDockWidgetArea, "Extractions")
        self._pipe_form = ApiPipelineForm(); self._pipe_form.added.connect(self._on_pipeline_added); self._pipe_form.deleted.connect(self._on_pipeline_deleted); self._pipe_form.edited.connect(self._on_pipeline_edited); self._pipe_dock = QDockWidget("Pipeline", self); self._pipe_dock.setWidget(self._pipe_form); self._add_dock(self._pipe_dock, Qt.DockWidgetArea.RightDockWidgetArea, "Pipeline")
        self.tabifyDockWidget(self._assert_dock, self._extract_dock); self.tabifyDockWidget(self._extract_dock, self._pipe_dock); self._assert_dock.raise_()
        
        # 3. Central Views (Added as Tabs instead of Docks)
        self._variable_manager = ApiVariableManager(self); self._variable_manager.variables_changed.connect(self._on_builder_changed)
        self._main_tabs.addTab(self._variable_manager, "📊 Variables")
        
        self._diagram_dock_widget = ApiDiagramDock(self); self._diagram_dock_widget.step_selected.connect(self._open_step_in_tab)
        self._main_tabs.addTab(self._diagram_dock_widget, "🗺 Workflow Map")
        
        self._code_dock_widget = ApiCodeDock(self); self._code_dock_widget.code_modified.connect(self._on_manual_code_edit)
        self._main_tabs.addTab(self._code_dock_widget, "🐍 PyShaft Code")
        
        self._history_dock_widget = ApiHistoryDock(self); self._history_dock_widget.request_restored.connect(self._open_step_in_tab)
        self._main_tabs.addTab(self._history_dock_widget, "🕒 History")

        # Hide docks by default (except Explorer)
        for dock in self._docks:
            if dock != self._explorer_dock:
                dock.hide()

    def toggle_explorer(self):
        self._explorer_dock.setVisible(not self._explorer_dock.isVisible())
        self._btn_toggle_explorer.setChecked(self._explorer_dock.isVisible())
 
    def _switch_mode(self, index: int) -> None:
        self._main_tabs.setCurrentIndex(index)
        if index == 4: # History
             self._history_dock_widget.refresh_history()

    def _build_menu(self) -> None:
        menubar = self.menuBar(); file_menu = menubar.addMenu("&File")
        file_menu.addAction("🆕 New Workflow", self._new_workflow); file_menu.addSeparator()
        file_menu.addAction("📂 Open Workflow...", self._open_workflow); file_menu.addAction("💾 Save Workflow...", self._save_workflow); file_menu.addSeparator()
        file_menu.addAction("🌐 Import cURL...", self._import_curl)
        file_menu.addAction("📮 Import Postman Collection...", self._import_postman)
        file_menu.addAction("📮 Import Postman Environment...", self._import_postman_env)
        file_menu.addAction("🐍 Import PyShaft .py...", self._import_pyshaft_script)
        file_menu.addSeparator()
        file_menu.addAction("📄 Export Workflow Docs (HTML)...", lambda: self._export_html_docs())
        file_menu.addSeparator()
        file_menu.addAction("🗑 Clear History", self._clear_history); file_menu.addAction("❌ Exit", self.close)
        edit_menu = menubar.addMenu("&Edit"); edit_menu.addAction("🔍 Global Search...", QKeySequence("Ctrl+Shift+F"), self._open_search)
        view_menu = menubar.addMenu("&View"); 
        for dock in self._docks: view_menu.addAction(dock.toggleViewAction())

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main"); tb.setMovable(False); tb.setStyleSheet(f"background: {COLORS['bg_dark']}; padding: 4px;")
        btn_preview = QPushButton("👁 Preview"); btn_preview.setStyleSheet(f"background: {COLORS['accent_blue']}22; color: {COLORS['accent_blue']}; font-weight: 700; padding: 6px 14px;"); btn_preview.clicked.connect(self._preview_current_request); tb.addWidget(btn_preview)
        btn_send = QPushButton("▶ Send"); btn_send.setStyleSheet(f"background: {COLORS['accent_green']}22; color: {COLORS['accent_green']}; font-weight: 700; padding: 6px 14px;"); btn_send.clicked.connect(self._run_current_tab); tb.addWidget(btn_send)
        tb.addSeparator()
        self._env_combo = QComboBox()
        self._env_combo.addItem("Default", -1)
        self._env_combo.currentIndexChanged.connect(self._on_env_changed)
        tb.addWidget(QLabel(" 🌍 "))
        tb.addWidget(self._env_combo)

        self._btn_remove_env = QPushButton("🗑")
        self._btn_remove_env.setToolTip("Remove selected environment")
        self._btn_remove_env.setFixedWidth(28)
        self._btn_remove_env.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {COLORS['text_muted']}; border: none;"
            f" font-size: 13px; border-radius: 3px; }}"
            f" QPushButton:hover {{ color: {COLORS['error']}; background: {COLORS['bg_hover']}; }}"
        )
        self._btn_remove_env.setEnabled(False)  # disabled on Default
        self._btn_remove_env.clicked.connect(self._remove_current_env)
        tb.addWidget(self._btn_remove_env)
        
        tb.addSeparator()
        self._btn_toggle_explorer = QPushButton("🗂 Explorer"); self._btn_toggle_explorer.setCheckable(True); self._btn_toggle_explorer.setChecked(True); self._btn_toggle_explorer.clicked.connect(lambda _: self.toggle_explorer()); tb.addWidget(self._btn_toggle_explorer)
        
        tb.addSeparator()
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["🛠 Builder", "📊 Variables", "🗺 Workflow Map", "🐍 PyShaft Code", "🕒 History"])
        self._mode_combo.currentIndexChanged.connect(self._switch_mode)
        tb.addWidget(QLabel(" 🚀 Mode: "))
        tb.addWidget(self._mode_combo)
        
        tb.addSeparator(); btn_export_md = QPushButton("📝 Export MD"); btn_export_md.clicked.connect(self._export_to_markdown); tb.addWidget(btn_export_md)
        tb.addSeparator(); btn_add = QPushButton("➕ Request"); btn_add.clicked.connect(self._add_root_request); tb.addWidget(btn_add); self.addToolBar(tb)

    def _build_statusbar(self) -> None: self._status_label = QLabel("Ready"); self.statusBar().addPermanentWidget(self._status_label)

    def _setup_shortcuts(self) -> None:
        act_send = QAction(self); act_send.setShortcut(QKeySequence("Ctrl+Return")); act_send.triggered.connect(self._run_current_tab); self.addAction(act_send)
        act_search = QAction(self); act_search.setShortcut(QKeySequence("Ctrl+F")); act_search.triggered.connect(self._open_search); self.addAction(act_search)

    def _new_workflow(self) -> None:
        """Discard current workflow and start fresh."""
        if QMessageBox.question(self, "New Workflow", "Discard current and start new?") == QMessageBox.StandardButton.Yes:
            from pyshaft.recorder.api_inspector.api_models import ApiWorkflow
            self._workflow = ApiWorkflow(); self._tabs.clear(); self._refresh_explorer()

    def _clear_history(self) -> None:
        """Clear history log."""
        self._history_dock_widget.clear_history(); self._status_label.setText("History cleared.")

    def _open_search(self) -> None:
        """Open global search dialog."""
        dialog = ApiSearchDialog(self._workflow, self); dialog.result_selected.connect(self._open_step_in_tab); dialog.exec()

    def _on_manual_code_edit(self, code: str) -> None:
        if "api.request()" not in code: return
        try:
            from pyshaft.recorder.api_inspector.api_importers import parse_pyshaft_script
            temp_path = Path.home() / ".pyshaft_sync_temp.py"; temp_path.write_text(code, encoding="utf-8")
            new_steps = parse_pyshaft_script(str(temp_path))
            if new_steps and len(new_steps) == len(self._workflow.all_steps):
                all_steps = self._workflow.all_steps
                for i, ns in enumerate(new_steps):
                    orig = all_steps[i]; orig.method, orig.url, orig.payload = ns.method, ns.url, ns.payload; orig.expected_status, orig.assertions = ns.expected_status, ns.assertions
                self._refresh_explorer(); self._status_label.setText("Code synced to GUI.")
        except: pass

    def _on_response_data_edited(self, new_data: Any) -> None:
        """Update step model when response is manually edited in UI."""
        builder = self._tabs.currentWidget()
        if isinstance(builder, ApiRequestBuilder):
            builder.step.last_response = new_data
            self._on_builder_changed()
            self._status_label.setText("Response body modified manually.")

    def _on_builder_changed(self) -> None:
        b = self._tabs.currentWidget()
        if isinstance(b, ApiRequestBuilder): b.save_to_step()
        self._code_dock_widget.update_code(self._workflow, scope=self._current_scope)
        self._diagram_dock_widget.update_diagram(self._workflow); self._update_tab_names()
        self._save_last_session()

    def _on_context_selected(self, item) -> None:
        """Update code dock scope when the user clicks an item in the Explorer."""
        from pyshaft.recorder.api_inspector.api_models import ApiRequestStep, ApiFolder
        if isinstance(item, (ApiRequestStep, ApiFolder)):
            self._current_scope = item
        else:
            self._current_scope = None  # Fall back to whole workflow
        self._code_dock_widget.update_code(self._workflow, scope=self._current_scope)

    def _on_assertion_added(self, a: ApiAssertion) -> None:
        b = self._tabs.currentWidget()
        if isinstance(b, ApiRequestBuilder):
            if a not in b.step.assertions: b.step.assertions.append(a)
            self._on_builder_changed(); self._assert_form.load_data(b.step.assertions)

    def _on_assertion_edited(self, old: ApiAssertion, new: ApiAssertion) -> None:
        b = self._tabs.currentWidget()
        if isinstance(b, ApiRequestBuilder) and old in b.step.assertions:
            idx = b.step.assertions.index(old); b.step.assertions[idx] = new; self._on_builder_changed(); self._assert_form.load_data(b.step.assertions)

    def _on_assertion_deleted(self, a: ApiAssertion) -> None:
        b = self._tabs.currentWidget()
        if isinstance(b, ApiRequestBuilder) and a in b.step.assertions:
            b.step.assertions.remove(a); self._on_builder_changed(); self._assert_form.load_data(b.step.assertions)

    def _on_extraction_added(self, e: ApiExtraction) -> None:
        b = self._tabs.currentWidget()
        if isinstance(b, ApiRequestBuilder):
            if e not in b.step.extractions: b.step.extractions.append(e)
            self._on_builder_changed(); self._extract_form.load_data(b.step.extractions)

    def _on_extraction_edited(self, old: ApiExtraction, new: ApiExtraction) -> None:
        b = self._tabs.currentWidget()
        if isinstance(b, ApiRequestBuilder) and old in b.step.extractions:
            idx = b.step.extractions.index(old); b.step.extractions[idx] = new; self._on_builder_changed(); self._extract_form.load_data(b.step.extractions)

    def _on_extraction_deleted(self, e: ApiExtraction) -> None:
        b = self._tabs.currentWidget()
        if isinstance(b, ApiRequestBuilder) and e in b.step.extractions:
            b.step.extractions.remove(e); self._on_builder_changed(); self._extract_form.load_data(b.step.extractions)

    def _on_pipeline_added(self, p: PipelineStep) -> None:
        b = self._tabs.currentWidget()
        if isinstance(b, ApiRequestBuilder):
            if p not in b.step.pipeline: b.step.pipeline.append(p)
            self._pipe_form.load_data(b.step.pipeline); self._on_builder_changed()

    def _on_pipeline_edited(self, old: PipelineStep, new: PipelineStep) -> None:
        b = self._tabs.currentWidget()
        if isinstance(b, ApiRequestBuilder) and old in b.step.pipeline:
            idx = b.step.pipeline.index(old); b.step.pipeline[idx] = new; self._on_builder_changed(); self._pipe_form.load_data(b.step.pipeline)


    def _on_pipeline_deleted(self, p: PipelineStep) -> None:
        b = self._tabs.currentWidget()
        if isinstance(b, ApiRequestBuilder) and p in b.step.pipeline:
            b.step.pipeline.remove(p); self._pipe_form.load_data(b.step.pipeline); self._on_builder_changed()

    def _on_quick_assertion(self, path: str, data: dict[str, Any]) -> None:
        b = self._tabs.currentWidget()
        if not isinstance(b, ApiRequestBuilder): return
        mode, val = data.get("mode", "equals"), data.get("value", "")
        if mode == "edit":
            existing = next((a for a in b.step.assertions if a.path == path), None)
            if existing: self._assert_dock.show(); self._assert_dock.raise_(); self._assert_form.start_edit(existing)
            return
        from pyshaft.recorder.api_inspector.api_models import AssertionType
        t = AssertionType.JSON_PATH_EQUALS
        if mode == "contains": t = AssertionType.JSON_PATH_CONTAINS
        elif mode == "type": t = AssertionType.JSON_PATH_TYPE
        elif mode == "deep_equals": t = AssertionType.DEEP_EQUALS
        elif mode == "deep_contains": t = AssertionType.DEEP_CONTAINS
        
        # For deep equal types, store the expected as JSON string
        if mode in ("deep_equals", "deep_contains"):
            import json
            expected_str = json.dumps(val, indent=2)
        else:
            expected_str = str(val)
        
        new_a = ApiAssertion(type=t, path=path, expected=expected_str)
        self._on_assertion_added(new_a); self._assert_dock.show(); self._assert_dock.raise_()

    def _on_schema_assertion(self, path: str, schema_json: str) -> None:
        """Create a JSON_SCHEMA assertion from the generated schema."""
        b = self._tabs.currentWidget()
        if not isinstance(b, ApiRequestBuilder): return
        from pyshaft.recorder.api_inspector.api_models import AssertionType
        new_a = ApiAssertion(type=AssertionType.JSON_SCHEMA, path=path, expected=schema_json)
        self._on_assertion_added(new_a)
        self._assert_dock.show(); self._assert_dock.raise_()
        self._status_label.setText(f"Schema assertion added for {path}")

    def _on_quick_extraction(self, path: str, value: Any) -> None:
        b = self._tabs.currentWidget()
        if not isinstance(b, ApiRequestBuilder): return
        var, ok = QInputDialog.getText(self, "Extract", f"Var for {path}:")
        if ok and var: self._on_extraction_added(ApiExtraction(variable_name=var, json_path=path))

    def _on_quick_remove_assertion(self, path: str) -> None:
        b = self._tabs.currentWidget()
        if isinstance(b, ApiRequestBuilder):
            b.step.assertions = [a for a in b.step.assertions if a.path != path]; self._assert_form.load_data(b.step.assertions); self._on_builder_changed()

    def _on_response_received(self, status: int, body: Any, dur: float, err: str, step: ApiRequestStep) -> None:
        if err:
            self._status_label.setText(f"❌ Error: {err}")
            self._resp_status_label.setText("ERROR")
            self._resp_status_label.setStyleSheet(f"color: {COLORS['error']}; font-weight: 700;")
            self._resp_time_label.setText("")
        else:
            self._status_label.setText(f"✓ {status} ({dur:.0f}ms)")
            
            # Update Response Metadata
            self._resp_status_label.setText(str(status))
            status_color = COLORS['success'] if status < 400 else COLORS['error']
            self._resp_status_label.setStyleSheet(f"color: {status_color}; font-weight: 700; font-size: 10pt;")
            self._resp_time_label.setText(f"{dur:.0f} ms")
            
            self._response_viewer.set_data(body)
            self._history_dock_widget.add_entry(step)
        self._refresh_explorer()
        self._code_dock_widget.update_code(self._workflow, scope=self._current_scope)

    def _run_current_tab(self) -> None:
        b = self._tabs.currentWidget()
        if isinstance(b, ApiRequestBuilder):
            b.save_to_step(); self._status_label.setText(f"Sending {b.step.name}..."); threading.Thread(target=self._execute_step, args=(b.step,), daemon=True).start()

    def _preview_current_request(self) -> None:
        """Show a preview dialog with the request details before sending."""
        b = self._tabs.currentWidget()
        if not isinstance(b, ApiRequestBuilder):
            return
        
        b.save_to_step()
        step = b.step
        
        # Resolve all variables to show final values
        url = self._resolve_url(step)
        headers = self._resolve_headers(step)
        payload = self._resolve_payload(step)
        
        # Build preview text
        preview_lines = [
            f"📡 {step.method.value} Request Preview",
            "=" * 50,
            f"\n🌐 URL:\n{url}",
            f"\n📋 Method: {step.method.value}",
            f"\n📑 Headers:",
        ]
        for k, v in headers.items():
            preview_lines.append(f"    {k}: {v}")
        
        preview_lines.append(f"\n📦 Body:")
        if payload:
            import json
            preview_lines.append(json.dumps(payload, indent=2))
        else:
            preview_lines.append("    (empty)")
        
        preview_lines.append("\n" + "=" * 50)
        
        # Show in a message box
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("Request Preview")
        msg.setText("\n".join(preview_lines))
        msg.setMinimumSize(600, 400)
        msg.exec()

    def _execute_step(self, step: ApiRequestStep) -> None:
        start = time.time()
        try:
            url = self._resolve_url(step)
            headers = self._resolve_headers(step)
            payload = self._resolve_payload(step)
            print(f"[DEBUG] ===== FINAL REQUEST =====")  # DEBUG
            print(f"[DEBUG] Method: {step.method.value}")  # DEBUG
            print(f"[DEBUG] URL: {url}")  # DEBUG
            print(f"[DEBUG] Headers: {headers}")  # DEBUG
            print(f"[DEBUG] Body (json): {payload}")  # DEBUG
            print(f"[DEBUG] ========================")  # DEBUG
            m = step.method.value.upper(); kwargs = {"headers": headers, "timeout": 30}
            if m in ("POST", "PUT", "PATCH") and payload: kwargs["json"] = payload
            resp = self._session.request(m, url, **kwargs); dur = (time.time() - start) * 1000
            try: body = resp.json()
            except: body = resp.text
            step.last_status, step.last_response, step.last_duration_ms = resp.status_code, body, dur
            self._handle_extractions(step, body); self._bridge.response_received.emit(resp.status_code, body, dur, "", step)
        except Exception as e:
            import traceback; logger.error(traceback.format_exc())
            self._bridge.response_received.emit(0, None, 0, str(e), step)

    def _handle_extractions(self, step: ApiRequestStep, response: Any) -> None:
        if not step.extractions or not isinstance(response, (dict, list)): return
        import jsonpath_ng
        for ext in step.extractions:
            try:
                expr = jsonpath_ng.parse(ext.json_path); matches = expr.find(response)
                if matches: self._workflow.variables[ext.variable_name] = str(matches[0].value)
            except: pass

    def _get_active_variables(self) -> dict[str, str]:
        vars = self._workflow.variables.copy(); idx = self._workflow.current_environment_index
        if 0 <= idx < len(self._workflow.environments): vars.update(self._workflow.environments[idx].variables)
        return vars

    # ── Dynamic variable resolution (Postman-compatible) ─────────────────────
    _DYNAMIC_VAR_RE = re.compile(r"\{\{\$(\w+)\}\}")

    def _resolve_dynamic_vars(self, text: str) -> str:
        """Replace {{$variableName}} Postman-style built-ins with generated values.

        Supported:
          $randomInt            – random integer 0-1000
          $randomIntRange(n,m)  – not yet; falls back to randomInt
          $guid / $uuid         – random UUID v4
          $timestamp            – Unix epoch seconds (integer)
          $isoTimestamp         – ISO-8601 UTC timestamp
          $randomFloat          – random float 0.0-1.0 (6 decimal places)
          $randomBoolean        – true or false
          $randomAlphaNumeric   – single random alphanumeric character
          $randomHexadecimal    – #xxxxxx hex colour
          $randomColor          – English colour name
          $randomFirstName      – random first name
          $randomLastName       – random last name
          $randomFullName       – random full name
          $randomEmail          – random email address
          $randomUserName       – random username
          $randomWord           – random English-ish word
          $randomWords          – random phrase
          $randomLoremWord      – random Lorem-style word
          $randomUrl            – random URL
          $randomCity           – random city name
          $randomStreetAddress  – random street address
          $randomCountry        – random country name
          $randomCountryCode    – random ISO country code
          $randomLatitude       – random latitude
          $randomLongitude      – random longitude
          $randomAbbreviation   – random abbreviation
          $randomNoun           – random noun
          $randomVerb           – random verb
          $randomAdjective      – random adjective
        """
        _FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank", "Ivy", "Jack"]
        _LAST_NAMES  = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Moore", "Taylor"]
        _CITIES      = ["Cairo", "London", "Paris", "Tokyo", "Berlin", "Sydney", "Dubai", "Toronto", "Madrid", "Rome"]
        _COUNTRIES   = ["Egypt", "United Kingdom", "France", "Japan", "Germany", "Australia", "UAE", "Canada", "Spain", "Italy"]
        _CODES       = ["EG", "GB", "FR", "JP", "DE", "AU", "AE", "CA", "ES", "IT"]
        _COLORS      = ["red", "blue", "green", "yellow", "purple", "orange", "pink", "black", "white", "cyan"]
        _WORDS       = ["apple", "river", "cloud", "forest", "stone", "ember", "thunder", "silver", "ocean", "drift"]
        _NOUNS       = ["cat", "bridge", "fire", "wave", "mountain", "shadow", "dawn", "leaf", "spark", "mirror"]
        _VERBS       = ["run", "jump", "fly", "swim", "sing", "dance", "climb", "build", "write", "think"]
        _ADJS        = ["quick", "lazy", "bright", "dark", "cold", "warm", "sharp", "soft", "loud", "silent"]

        def _gen(name: str) -> str:
            n = name.lower()
            if n == "randomint":           return str(random.randint(0, 1000))
            if n == "guid" or n == "uuid": return str(uuid.uuid4())
            if n == "timestamp":           return str(int(time.time()))
            if n == "isotimestamp":        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if n == "randomfloat":         return f"{random.random():.6f}"
            if n == "randomboolean":       return random.choice(["true", "false"])
            if n == "randomalphanumeric":  return random.choice(string.ascii_letters + string.digits)
            if n == "randomhexadecimal":   return "#{:06x}".format(random.randint(0, 0xFFFFFF))
            if n == "randomcolor":         return random.choice(_COLORS)
            if n == "randomfirstname":     return random.choice(_FIRST_NAMES)
            if n == "randomlastname":      return random.choice(_LAST_NAMES)
            if n == "randomfullname":      return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"
            if n == "randomemail":         fn = random.choice(_FIRST_NAMES).lower(); ln = random.choice(_LAST_NAMES).lower(); return f"{fn}.{ln}{random.randint(1, 999)}@example.com"
            if n == "randomusername":      fn = random.choice(_FIRST_NAMES).lower(); return f"{fn}{random.randint(100, 9999)}"
            if n in ("randomword", "randomloremword"): return random.choice(_WORDS)
            if n == "randomwords":         return " ".join(random.choices(_WORDS, k=3))
            if n == "randomurl":           w = random.choice(_WORDS); return f"https://www.{w}.com"
            if n == "randomcity":          return random.choice(_CITIES)
            if n == "randomstreetaddress": return f"{random.randint(1, 999)} {random.choice(_WORDS).title()} St"
            if n == "randomcountry":       return random.choice(_COUNTRIES)
            if n == "randomcountrycode":   return random.choice(_CODES)
            if n == "randomlatitude":      return f"{random.uniform(-90, 90):.6f}"
            if n == "randomlongitude":     return f"{random.uniform(-180, 180):.6f}"
            if n == "randomabbreviation":  return "".join(random.choices(string.ascii_uppercase, k=random.randint(2, 4)))
            if n == "randomnoun":          return random.choice(_NOUNS)
            if n == "randomverb":          return random.choice(_VERBS)
            if n == "randomadjective":     return random.choice(_ADJS)
            # Unknown — leave as-is
            return "{{$" + name + "}}"

        return self._DYNAMIC_VAR_RE.sub(lambda m: _gen(m.group(1)), text)

    def _resolve_url(self, step: ApiRequestStep) -> str:
        import urllib.parse
        url = step.url or step.endpoint; idx = self._workflow.current_environment_index
        env_base = self._workflow.environments[idx].base_url if 0 <= idx < len(self._workflow.environments) else ""
        base = env_base or self._workflow.base_url
        if not url.startswith("http") and base: url = f"{base.rstrip('/')}/{url.lstrip('/')}"
        active_vars = self._get_active_variables()
        for vn, vv in active_vars.items():
            actual = os.environ.get(vv[1:], vv) if isinstance(vv, str) and vv.startswith("$") else vv
            url = url.replace(f"{{{{{vn}}}}}", str(actual))
        # Resolve built-in dynamic variables (e.g. {{$randomInt}})
        url = self._resolve_dynamic_vars(url)

        # Ensure url has a scheme so requests library doesn't fail
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"

        # Append plain query params from the Params tab (with variable substitution)
        query_params: dict = getattr(step, "query_params", {})
        if query_params:
            parsed = urllib.parse.urlsplit(url)
            qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            for k, v in query_params.items():
                # Apply variable substitution to key/value
                for vn, vv in active_vars.items():
                    actual = os.environ.get(vv[1:], vv) if isinstance(vv, str) and vv.startswith("$") else vv
                    k = k.replace(f"{{{{{vn}}}}}", str(actual))
                    v = v.replace(f"{{{{{vn}}}}}", str(actual))
                k = self._resolve_dynamic_vars(k)
                v = self._resolve_dynamic_vars(v)
                qs[k] = [v]
            new_query = urllib.parse.urlencode({k: v[0] for k, v in qs.items()})
            url = urllib.parse.urlunsplit(parsed._replace(query=new_query))

        return url

    def _resolve_headers(self, step: ApiRequestStep) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}; headers.update(step.headers); active_vars = self._get_active_variables()
        for k, v in list(headers.items()):
            for vn, vv in active_vars.items():
                actual = os.environ.get(vv[1:], vv) if isinstance(vv, str) and vv.startswith("$") else vv
                v = v.replace(f"{{{{{vn}}}}}", str(actual))
            headers[k] = self._resolve_dynamic_vars(v)
        return headers

    def _resolve_payload(self, step: ApiRequestStep) -> Any:
        if not step.payload: return None
        ps = step.payload
        print(f"[DEBUG] Raw payload: {ps[:200]}", flush=True)  # DEBUG
        active_vars = self._get_active_variables()
        for vn, vv in active_vars.items():
            actual = os.environ.get(vv[1:], vv) if isinstance(vv, str) and vv.startswith("$") else vv
            ps = ps.replace(f"{{{{{vn}}}}}", str(actual))
        print(f"[DEBUG] After var substitution: {ps[:200]}", flush=True)  # DEBUG
        ps = self._resolve_dynamic_vars(ps)
        print(f"[DEBUG] After dynamic vars: {ps[:200]}", flush=True)  # DEBUG
        try: 
            result = json.loads(ps)
            print(f"[DEBUG] JSON parsed successfully: {result}", flush=True)  # DEBUG
            return result
        except Exception as e:
            print(f"[DEBUG] JSON parse failed: {e}, returning raw string", flush=True)  # DEBUG
            return ps

    def _open_workflow(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open", "", "JSON (*.json)")
        if path: self._workflow = load_workflow(path); self._refresh_explorer()

    def _save_workflow(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save", "workflow.json", "JSON (*.json)")
        if path: save_workflow(self._workflow, path)

    def _export_html_docs(self, item=None) -> None:
        """Export HTML docs for the entire workflow, or a specific folder/request."""
        target_item = item or self._workflow
        default_name = "workflow_docs.html"
        if hasattr(target_item, "name") and target_item.name:
            default_name = f"{target_item.name.replace(' ', '_').lower()}_docs.html"
            
        path, _ = QFileDialog.getSaveFileName(self, "Export HTML Docs", default_name, "HTML Files (*.html)")
        if path:
            try:
                from pyshaft.recorder.api_inspector.api_doc_generator import generate_html_docs
                active_vars = self._get_active_variables()
                generate_html_docs(target_item, path, variables=active_vars)
                self._status_label.setText(f"✓ Exported HTML docs to {path}")
                import webbrowser
                webbrowser.open(f"file:///{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to generate documentation:\n{e}")

    def _import_curl(self) -> None:
        text, ok = QInputDialog.getMultiLineText(self, "cURL", "Paste:")
        if ok and text:
            from pyshaft.recorder.api_inspector.api_importers import parse_curl
            step = parse_curl(text); self._workflow.items.append(step); self._refresh_explorer(); self._open_step_in_tab(step)

    def _import_postman(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Postman Collection", "", "JSON (*.json)")
        if path:
            try:
                from pyshaft.recorder.api_inspector.api_importers import parse_postman_collection_full
                result = parse_postman_collection_full(path)
                
                # Auto-create an environment for this collection's variables
                if result.variables:
                    from pyshaft.recorder.api_inspector.api_models import ApiEnvironment
                    env_name = f"{result.collection_name} Env"
                    new_env = ApiEnvironment(name=env_name, variables=result.variables)
                    self._workflow.environments.append(new_env)
                    # Set the new environment as active
                    self._workflow.current_environment_index = len(self._workflow.environments) - 1
                
                # Add imported items
                self._workflow.items.extend(result.items)
                
                self._refresh_explorer()
                self._status_label.setText(f"Imported Postman Collection: {result.collection_name}")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import Postman Collection:\n{e}")

    def _import_postman_env(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Postman Environment", "", "JSON (*.json)")
        if path:
            try:
                from pyshaft.recorder.api_inspector.api_importers import parse_postman_environment, scan_and_register_template_vars
                variables = parse_postman_environment(path)
                
                # Scan current workflow to add missing template variables into this environment
                scan_and_register_template_vars(self._workflow.items, variables)
                
                import os
                env_name = os.path.splitext(os.path.basename(path))[0]
                
                from pyshaft.recorder.api_inspector.api_models import ApiEnvironment
                new_env = ApiEnvironment(name=env_name, variables=variables)
                self._workflow.environments.append(new_env)
                
                self._refresh_explorer()
                self._status_label.setText(f"Imported Postman Environment: {env_name}")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import Postman Environment:\n{e}")

    def _import_pyshaft_script(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import PyShaft", "", "Python (*.py)")
        if path:
            try:
                from pyshaft.recorder.api_inspector.api_importers import parse_pyshaft_script
                steps = parse_pyshaft_script(path); self._workflow.items.extend(steps); self._refresh_explorer(); self._status_label.setText(f"Imported {len(steps)} steps.")
            except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def _on_env_changed(self, index: int) -> None:
        self._workflow.current_environment_index = self._env_combo.itemData(index)
        self._variable_manager.set_workflow(self._workflow)
        # Enable remove button only when a real (non-Default) env is selected
        is_real_env = self._env_combo.itemData(index) != -1
        self._btn_remove_env.setEnabled(is_real_env)

    def _remove_current_env(self) -> None:
        """Remove the currently selected environment from the workflow."""
        idx = self._env_combo.currentIndex()
        env_index: int = self._env_combo.itemData(idx)
        if env_index == -1:
            return  # Can't remove Default
        env_name = self._env_combo.currentText()
        reply = QMessageBox.question(
            self, "Remove Environment",
            f"Remove environment '{env_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        # Remove from model
        if 0 <= env_index < len(self._workflow.environments):
            self._workflow.environments.pop(env_index)
        # Reset active env to Default
        self._workflow.current_environment_index = -1
        self._refresh_env_list()
        self._variable_manager.set_workflow(self._workflow)
        self._status_label.setText(f"Removed environment: {env_name}")
        self._save_last_session()

    def _manage_environments(self) -> None:
        n, ok = QInputDialog.getText(self, "Env", "Name:")
        if ok and n:
            u, ok2 = QInputDialog.getText(self, "URL", f"URL for {n}:")
            if ok2: self._workflow.environments.append(ApiEnvironment(name=n, base_url=u)); self._refresh_env_list()

    def _refresh_env_list(self) -> None:
        self._env_combo.blockSignals(True); self._env_combo.clear(); self._env_combo.addItem("Default", -1)
        for i, env in enumerate(self._workflow.environments): self._env_combo.addItem(env.name, i)
        curr = self._workflow.current_environment_index
        for i in range(self._env_combo.count()):
            if self._env_combo.itemData(i) == curr: self._env_combo.setCurrentIndex(i); break
        self._env_combo.blockSignals(False)

    def _refresh_explorer(self, refresh_explorer: bool = True) -> None:
        if refresh_explorer:
            self._explorer_dock.set_workflow(self._workflow)
        self._diagram_dock_widget.update_diagram(self._workflow)
        self._save_last_session()
        self._update_tab_names(); self._refresh_env_list(); self._variable_manager.set_workflow(self._workflow)

    def _update_tab_names(self) -> None:
        for i in range(self._tabs.count()):
            builder = self._tabs.widget(i)
            if isinstance(builder, ApiRequestBuilder): self._tabs.setTabText(i, builder.step.name)

    def _open_step_in_tab(self, step: ApiRequestStep) -> None:
        self._main_tabs.setCurrentIndex(0) # Switch to Builder
        for i in range(self._tabs.count()):
            builder = self._tabs.widget(i)
            if isinstance(builder, ApiRequestBuilder) and builder.step == step:
                self._tabs.setCurrentIndex(i); return
        builder = ApiRequestBuilder(step); builder.changed.connect(self._on_builder_changed)
        idx = self._tabs.addTab(builder, step.name); self._tabs.setCurrentIndex(idx)

    def _on_item_deleted_refresh(self, refresh_explorer: bool = True) -> None:
        for i in range(self._tabs.count() - 1, -1, -1):
            builder = self._tabs.widget(i)
            if isinstance(builder, ApiRequestBuilder) and builder.step not in self._workflow.all_steps: self._tabs.removeTab(i)
        # Reset scope if the scoped item was deleted
        if self._current_scope not in self._workflow.all_steps:
            from pyshaft.recorder.api_inspector.api_models import ApiFolder
            if not isinstance(self._current_scope, ApiFolder) or self._current_scope not in [
                f for f in self._workflow.items if isinstance(f, ApiFolder)
            ]:
                self._current_scope = None
        self._refresh_explorer(refresh_explorer=refresh_explorer); self._save_last_session()
        self._code_dock_widget.update_code(self._workflow, scope=self._current_scope)

    def _add_root_request(self) -> None:
        step = ApiRequestStep(name=f"Request {len(self._workflow.all_steps) + 1}")
        self._workflow.items.append(step); self._refresh_explorer(); self._open_step_in_tab(step)

    def _toggle_focus(self, mode: str, checked: bool) -> None:
        """Generalized focus mode for all components."""
        for btn in [self._btn_focus_map, self._btn_focus_code, self._btn_focus_resp, self._btn_focus_exp, self._btn_focus_req]:
            if btn.text().lower().endswith(mode): continue
            btn.blockSignals(True); btn.setChecked(False); btn.blockSignals(False)

        self._focus_mode = checked
        target = {"map": self._diagram_dock, "code": self._code_dock, "resp": self._response_dock, "exp": self._explorer_dock}.get(mode)

        for d in self._docks:
            if checked: d.setVisible(d == target)
            else: d.setVisible(True)
        
        # Central Tabs logic
        if mode == "req":
            for d in self._docks: d.setVisible(not checked)
            self._tabs.setVisible(True)
        else:
            self._tabs.setVisible(not checked)
            
        self._status_label.setText(f"Focus: {mode.upper()}" if checked else "Ready")

    def _export_to_markdown(self) -> None:
        b = self._tabs.currentWidget()
        if not isinstance(b, ApiRequestBuilder): return
        s = b.step; md = f"# API Snapshot: {s.name}\n\n## Request\n- **Method**: `{s.method}`\n- **URL**: `{self._resolve_url(s)}`\n"
        if s.headers:
            md += "### Headers\n```yaml\n"
            for k, v in s.headers.items(): md += f"{k}: {v}\n"
            md += "```\n"
        if s.payload:
            md += "### Body\n```json\n"
            try: md += json.dumps(json.loads(s.payload), indent=2)
            except: md += s.payload
            md += "\n```\n\n"
        if s.last_response:
            md += f"## Response\n- **Status**: `{s.last_status}`\n- **Time**: `{s.last_duration_ms:.0f}ms`\n### Body\n```json\n"
            try: md += json.dumps(s.last_response, indent=2)
            except: md += str(s.last_response)
            md += "\n```\n"
            if s.assertions:
                md += "\n## Validations\n"
                for a in s.assertions: md += f"- [x] {a.type.value}: `{a.path}` == `{a.expected}`\n"
        else: md += "## Response\n*(No execution data recorded)*\n"
        path, _ = QFileDialog.getSaveFileName(self, "Export MD", f"request-response-{s.name.lower().replace(' ','-')}.md", "Markdown (*.md)")
        if path: Path(path).write_text(md, encoding="utf-8"); self._status_label.setText(f"Exported {Path(path).name}")

    def _on_tab_changed(self, index: int) -> None:
        if index >= 0:
            builder = self._tabs.widget(index)
            if isinstance(builder, ApiRequestBuilder):
                self._current_scope = builder.step
                self._load_step_context(builder.step)
                self._code_dock_widget.update_code(self._workflow, scope=self._current_scope)

    def _on_tab_close_requested(self, index: int) -> None: self._tabs.removeTab(index)

    def _on_json_path_selected(self, path: str, value: Any) -> None:
        self._assert_form.set_path(path, value); self._extract_form.set_path(path); self._pipe_form.set_path(path)

    def _load_step_context(self, step: ApiRequestStep) -> None:
        self._response_viewer.set_data(step.last_response); self._assert_form.load_data(step.assertions); self._extract_form.load_data(step.extractions); self._pipe_form.load_data(step.pipeline)

