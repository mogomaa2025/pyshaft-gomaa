"""PyShaft API Inspector — Environment and variable manager."""

from __future__ import annotations

from typing import TYPE_CHECKING
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDockWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QHeaderView,
    QComboBox,
    QTabWidget,
)

from pyshaft.recorder.theme import COLORS, FONTS

if TYPE_CHECKING:
    from pyshaft.recorder.api_inspector.api_models import ApiWorkflow, ApiEnvironment


class ApiVariableManager(QDockWidget):
    """Manager for global variables, environment variables, and global headers."""
    
    variables_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Variable Manager", parent)
        self.setObjectName("variable_manager")
        self._workflow: ApiWorkflow | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"QTabWidget::pane {{ border: none; }}")
        
        # ── Tab 1: Variables ──
        var_widget = QWidget()
        var_layout = QVBoxLayout(var_widget)
        var_layout.setContentsMargins(4, 4, 4, 4)
        
        row_env = QHBoxLayout()
        row_env.addWidget(QLabel("Environment:"))
        self._env_combo = QComboBox()
        self._env_combo.currentIndexChanged.connect(self._on_env_changed)
        row_env.addWidget(self._env_combo, 1)
        var_layout.addLayout(row_env)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Name", "Value"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setStyleSheet(self._table_style())
        self._table.itemChanged.connect(self._on_item_changed)
        var_layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("➕ Add Variable")
        btn_add.clicked.connect(self._add_row)
        btn_row.addWidget(btn_add)
        btn_del = QPushButton("🗑 Delete")
        btn_del.clicked.connect(self._delete_row)
        btn_row.addWidget(btn_del)
        var_layout.addLayout(btn_row)
        
        self._tabs.addTab(var_widget, "Variables")

        # ── Tab 2: Global Headers ──
        headers_widget = QWidget()
        headers_layout = QVBoxLayout(headers_widget)
        headers_layout.setContentsMargins(4, 4, 4, 4)
        
        self._headers_table = QTableWidget(0, 2)
        self._headers_table.setHorizontalHeaderLabels(["Header Key", "Value"])
        self._headers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._headers_table.setStyleSheet(self._table_style())
        self._headers_table.itemChanged.connect(self._on_header_changed)
        headers_layout.addWidget(self._headers_table)

        h_btn_row = QHBoxLayout()
        btn_h_add = QPushButton("➕ Add Header")
        btn_h_add.clicked.connect(self._add_header_row)
        h_btn_row.addWidget(btn_h_add)
        btn_h_del = QPushButton("🗑 Delete")
        btn_h_del.clicked.connect(self._delete_header_row)
        h_btn_row.addWidget(btn_h_del)
        headers_layout.addLayout(h_btn_row)
        
        self._tabs.addTab(headers_widget, "Global Headers")

        layout.addWidget(self._tabs)
        self.setWidget(container)

    def _table_style(self) -> str:
        return f"""
            QTableWidget {{ background: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']}; color: {COLORS['text_primary']}; }}
            QHeaderView::section {{ background: {COLORS['bg_darkest']}; color: {COLORS['text_muted']}; border: none; padding: 4px; }}
        """

    def set_workflow(self, workflow: ApiWorkflow) -> None:
        self._workflow = workflow
        self._refresh_env_list()
        self._load_variables()
        self._load_headers()

    def _refresh_env_list(self) -> None:
        if not self._workflow: return
        self._env_combo.blockSignals(True)
        self._env_combo.clear()
        self._env_combo.addItem("Global / Default", -1)
        for i, env in enumerate(self._workflow.environments):
            self._env_combo.addItem(env.name, i)
        
        curr = self._workflow.current_environment_index
        for i in range(self._env_combo.count()):
            if self._env_combo.itemData(i) == curr:
                self._env_combo.setCurrentIndex(i)
                break
        self._env_combo.blockSignals(False)

    def _load_variables(self) -> None:
        if not self._workflow: return
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        
        idx = self._env_combo.currentData()
        target_dict = self._workflow.variables if idx == -1 else self._workflow.environments[idx].variables
        
        for name, value in target_dict.items():
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(name))
            self._table.setItem(row, 1, QTableWidgetItem(str(value)))
            
        self._table.blockSignals(False)

    def _load_headers(self) -> None:
        if not self._workflow: return
        self._headers_table.blockSignals(True)
        self._headers_table.setRowCount(0)
        for k, v in self._workflow.global_headers.items():
            row = self._headers_table.rowCount()
            self._headers_table.insertRow(row)
            self._headers_table.setItem(row, 0, QTableWidgetItem(k))
            self._headers_table.setItem(row, 1, QTableWidgetItem(str(v)))
        self._headers_table.blockSignals(False)

    def _on_env_changed(self) -> None:
        if self._workflow:
            self._workflow.current_environment_index = self._env_combo.currentData()
            self._load_variables()
            self.variables_changed.emit()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if not self._workflow: return
        idx = self._env_combo.currentData()
        target_dict = self._workflow.variables if idx == -1 else self._workflow.environments[idx].variables
        
        row = item.row()
        name_item = self._table.item(row, 0)
        val_item = self._table.item(row, 1)
        
        if name_item and name_item.text().strip():
            target_dict[name_item.text().strip()] = val_item.text() if val_item else ""
            self.variables_changed.emit()

    def _on_header_changed(self, item: QTableWidgetItem) -> None:
        if not self._workflow: return
        row = item.row()
        k_item = self._headers_table.item(row, 0)
        v_item = self._headers_table.item(row, 1)
        if k_item and k_item.text().strip():
            self._workflow.global_headers[k_item.text().strip()] = v_item.text() if v_item else ""
            self.variables_changed.emit()

    def _add_row(self) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(f"var_{row+1}"))
        self._table.setItem(row, 1, QTableWidgetItem(""))

    def _delete_row(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            name_item = self._table.item(row, 0)
            if name_item and self._workflow:
                idx = self._env_combo.currentData()
                target_dict = self._workflow.variables if idx == -1 else self._workflow.environments[idx].variables
                if name_item.text() in target_dict:
                    del target_dict[name_item.text()]
            self._table.removeRow(row)
            self.variables_changed.emit()

    def _add_header_row(self) -> None:
        row = self._headers_table.rowCount()
        self._headers_table.insertRow(row)
        self._headers_table.setItem(row, 0, QTableWidgetItem("Header-Name"))
        self._headers_table.setItem(row, 1, QTableWidgetItem(""))

    def _delete_header_row(self) -> None:
        row = self._headers_table.currentRow()
        if row >= 0:
            name_item = self._headers_table.item(row, 0)
            if name_item and self._workflow:
                if name_item.text() in self._workflow.global_headers:
                    del self._workflow.global_headers[name_item.text()]
            self._headers_table.removeRow(row)
            self.variables_changed.emit()
