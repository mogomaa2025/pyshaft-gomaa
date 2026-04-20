"""PyShaft API Inspector — Specialized panels for assertions, extractions, and pipeline steps."""

from __future__ import annotations

from typing import Any
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
)

from pyshaft.recorder.api_inspector.api_models import (
    ApiAssertion,
    ApiExtraction,
    AssertionType,
    PipelineOp,
    PipelineStep,
)
from pyshaft.recorder.theme import COLORS, FONTS


class ListItemWidget(QWidget):
    """Custom widget for list items with Edit and Delete buttons."""
    edit_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)

    def __init__(self, text: str, data: Any, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.data = data
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(10)

        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setStyleSheet(f"color: {color}; font-size: {FONTS['size_sm']}; font-weight: 500; background: transparent; border: none;")
        layout.addWidget(self.label, 1)

        btn_style = f"""
            QPushButton {{
                background: {COLORS['bg_medium']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text_primary']};
                font-size: 14px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_hover']};
                border-color: {COLORS['accent_purple']};
                color: white;
            }}
        """

        self.btn_edit = QPushButton("✏")
        self.btn_edit.setFixedSize(26, 26)
        self.btn_edit.setStyleSheet(btn_style)
        self.btn_edit.clicked.connect(lambda: self.edit_requested.emit(self.data))
        layout.addWidget(self.btn_edit)

        self.btn_del = QPushButton("🗑")
        self.btn_del.setFixedSize(26, 26)
        self.btn_del.setStyleSheet(btn_style)
        self.btn_del.clicked.connect(lambda: self.delete_requested.emit(self.data))
        layout.addWidget(self.btn_del)

        self.setMinimumHeight(40)

    def sizeHint(self) -> QSize:
        return QSize(100, 40)


class ApiAssertionForm(QScrollArea):
    """Panel for building response assertions (Scrollable)."""
    added = pyqtSignal(object)
    deleted = pyqtSignal(object)
    edited = pyqtSignal(object, object) # (old, new)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self._editing_data: ApiAssertion | None = None
        
        self._container = QWidget()
        self.setWidget(self._container)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        
        row1 = QHBoxLayout()
        self._type_combo = QComboBox()
        for at in AssertionType:
            self._type_combo.addItem(at.value.replace("_", " ").title(), at)
        row1.addWidget(QLabel("Type:"))
        row1.addWidget(self._type_combo, 1)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        self._path_input = QLineEdit()
        self._path_input.setPlaceholderText("JSONPath")
        row2.addWidget(self._path_input, 1)
        self._expected_input = QLineEdit()
        self._expected_input.setPlaceholderText("Expected value")
        row2.addWidget(self._expected_input, 1)
        layout.addLayout(row2)

        btns = QHBoxLayout()
        self._add_btn = QPushButton("+ Add Assertion")
        self._add_btn.setStyleSheet(f"background: {COLORS['accent_green']}22; color: {COLORS['accent_green']}; font-weight: 600; padding: 8px;")
        self._add_btn.clicked.connect(self._on_add)
        btns.addWidget(self._add_btn, 1)
        
        self._cancel_btn = QPushButton("✕")
        self._cancel_btn.setFixedSize(34, 34); self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._cancel_edit)
        btns.addWidget(self._cancel_btn)
        layout.addLayout(btns)

        self._list = QListWidget()
        self._list.setMinimumHeight(200)
        self._list.setStyleSheet(f"background: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']};")
        layout.addWidget(self._list)
        layout.addStretch()

    def start_edit(self, assertion: ApiAssertion) -> None:
        self._editing_data = assertion
        self._path_input.setText(assertion.path)
        self._expected_input.setText(str(assertion.expected))
        idx = self._type_combo.findData(assertion.type)
        if idx >= 0: self._type_combo.setCurrentIndex(idx)
        self._add_btn.setText("💾 Save Changes"); self._cancel_btn.setVisible(True)

    def _cancel_edit(self) -> None:
        self._editing_data = None
        self._path_input.clear(); self._expected_input.clear()
        self._add_btn.setText("+ Add Assertion"); self._cancel_btn.setVisible(False)

    def set_path(self, path: str, value: Any = None) -> None:
        self._path_input.setText(path)
        if value is not None:
            self._expected_input.setText(str(value))
            if isinstance(value, int):
                idx = self._type_combo.findData(AssertionType.JSON_PATH_EQUALS)
                if idx >= 0: self._type_combo.setCurrentIndex(idx)
            elif isinstance(value, str):
                idx = self._type_combo.findData(AssertionType.JSON_PATH_CONTAINS)
                if idx >= 0: self._type_combo.setCurrentIndex(idx)

    def load_data(self, assertions: list[ApiAssertion]) -> None:
        self._list.clear()
        for a in assertions:
            text = f"✓ {a.type.value.replace('_',' ')}: {a.path} == {a.expected}"
            item = QListWidgetItem(self._list)
            widget = ListItemWidget(text, a, COLORS['accent_green'])
            widget.edit_requested.connect(self.start_edit)
            widget.delete_requested.connect(self.deleted.emit)
            item.setSizeHint(widget.sizeHint())
            self._list.setItemWidget(item, widget)

    def _on_add(self) -> None:
        a_type = self._type_combo.currentData()
        path = self._path_input.text().strip(); expected = self._expected_input.text().strip()
        if not path: return
        new_a = ApiAssertion(type=a_type, path=path, expected=expected)
        if self._editing_data: self.edited.emit(self._editing_data, new_a); self._cancel_edit()
        else: self.added.emit(new_a); self._path_input.clear(); self._expected_input.clear()

    def clear(self) -> None:
        self._path_input.clear(); self._expected_input.clear(); self._list.clear()


class ApiExtractionForm(QScrollArea):
    """Panel for extracting values to variables (Scrollable)."""
    added = pyqtSignal(object)
    deleted = pyqtSignal(object)
    edited = pyqtSignal(object, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._editing_data: ApiExtraction | None = None
        self._container = QWidget()
        self.setWidget(self._container)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        row = QHBoxLayout()
        self._var_input = QLineEdit(); self._var_input.setPlaceholderText("Var Name")
        row.addWidget(self._var_input, 1)
        self._path_input = QLineEdit(); self._path_input.setPlaceholderText("JSONPath")
        row.addWidget(self._path_input, 1)
        self._cast_combo = QComboBox(); self._cast_combo.addItems(["str", "int", "float", "bool"])
        row.addWidget(self._cast_combo)
        layout.addLayout(row)

        btns = QHBoxLayout()
        self._add_btn = QPushButton("+ Add Extraction")
        self._add_btn.setStyleSheet(f"background: {COLORS['accent_orange']}22; color: {COLORS['accent_orange']}; font-weight: 600; padding: 8px;")
        self._add_btn.clicked.connect(self._on_add)
        btns.addWidget(self._add_btn, 1)
        
        self._cancel_btn = QPushButton("✕")
        self._cancel_btn.setFixedSize(34, 34); self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._cancel_edit)
        btns.addWidget(self._cancel_btn)
        layout.addLayout(btns)

        self._list = QListWidget()
        self._list.setMinimumHeight(150)
        self._list.setStyleSheet(f"background: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']};")
        layout.addWidget(self._list)
        layout.addStretch()

    def start_edit(self, ext: ApiExtraction) -> None:
        self._editing_data = ext
        self._var_input.setText(ext.variable_name); self._path_input.setText(ext.json_path); self._cast_combo.setCurrentText(ext.cast_type)
        self._add_btn.setText("💾 Save"); self._cancel_btn.setVisible(True)

    def _cancel_edit(self) -> None:
        self._editing_data = None
        self._var_input.clear(); self._path_input.clear()
        self._add_btn.setText("+ Add Extraction"); self._cancel_btn.setVisible(False)

    def set_path(self, path: str) -> None: self._path_input.setText(path)

    def load_data(self, extractions: list[ApiExtraction]) -> None:
        self._list.clear()
        for ext in extractions:
            text = f"📦 {ext.variable_name} ← {ext.json_path}"
            item = QListWidgetItem(self._list)
            widget = ListItemWidget(text, ext, COLORS['accent_orange'])
            widget.edit_requested.connect(self.start_edit)
            widget.delete_requested.connect(self.deleted.emit)
            item.setSizeHint(widget.sizeHint())
            self._list.setItemWidget(item, widget)

    def _on_add(self) -> None:
        v = self._var_input.text().strip(); p = self._path_input.text().strip(); c = self._cast_combo.currentText()
        if not v or not p: return
        new_e = ApiExtraction(variable_name=v, json_path=p, cast_type=c)
        if self._editing_data: self.edited.emit(self._editing_data, new_e); self._cancel_edit()
        else: self.added.emit(new_e); self._var_input.clear(); self._path_input.clear()

    def clear(self) -> None: self._var_input.clear(); self._path_input.clear(); self._list.clear()


class ApiPipelineForm(QScrollArea):
    """Panel for data transformations (Scrollable)."""
    added = pyqtSignal(object)
    deleted = pyqtSignal(object)
    edited = pyqtSignal(object, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._editing_data: PipelineStep | None = None
        self._container = QWidget()
        self.setWidget(self._container)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        row = QHBoxLayout()
        self._op_combo = QComboBox()
        for op in PipelineOp: self._op_combo.addItem(op.value.title(), op)
        row.addWidget(self._op_combo)
        self._path_input = QLineEdit(); self._path_input.setPlaceholderText("JSONPath")
        row.addWidget(self._path_input, 1)
        self._expr_input = QLineEdit(); self._expr_input.setPlaceholderText("Expression")
        row.addWidget(self._expr_input, 1)
        layout.addLayout(row)

        btns = QHBoxLayout()
        self._add_btn = QPushButton("+ Add Transformation")
        self._add_btn.setStyleSheet(f"background: {COLORS['accent_purple']}22; color: {COLORS['accent_purple']}; font-weight: 600; padding: 8px;")
        self._add_btn.clicked.connect(self._on_add)
        btns.addWidget(self._add_btn, 1)

        self._cancel_btn = QPushButton("✕")
        self._cancel_btn.setFixedSize(34, 34); self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._cancel_edit)
        btns.addWidget(self._cancel_btn)
        layout.addLayout(btns)

        self._list = QListWidget()
        self._list.setMinimumHeight(150)
        self._list.setStyleSheet(f"background: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']};")
        layout.addWidget(self._list)
        layout.addStretch()

    def start_edit(self, p: PipelineStep) -> None:
        self._editing_data = p
        self._path_input.setText(p.path); self._expr_input.setText(p.expression)
        idx = self._op_combo.findData(p.operation)
        if idx >= 0: self._op_combo.setCurrentIndex(idx)
        self._add_btn.setText("💾 Save"); self._cancel_btn.setVisible(True)

    def _cancel_edit(self) -> None:
        self._editing_data = None
        self._path_input.clear(); self._expr_input.clear()
        self._add_btn.setText("+ Add Transformation"); self._cancel_btn.setVisible(False)

    def set_path(self, path: str) -> None: self._path_input.setText(path)

    def load_data(self, pipeline: list[PipelineStep]) -> None:
        self._list.clear()
        for p in pipeline:
            text = f"⛓ {p.operation.value}({p.path})"
            item = QListWidgetItem(self._list)
            widget = ListItemWidget(text, p, COLORS['accent_purple'])
            widget.edit_requested.connect(self.start_edit)
            widget.delete_requested.connect(self.deleted.emit)
            item.setSizeHint(widget.sizeHint())
            self._list.setItemWidget(item, widget)

    def _on_add(self) -> None:
        op = self._op_combo.currentData(); path = self._path_input.text().strip(); expr = self._expr_input.text().strip()
        if not path: return
        new_p = PipelineStep(operation=op, path=path, expression=expr)
        if self._editing_data: self.edited.emit(self._editing_data, new_p); self._cancel_edit()
        else: self.added.emit(new_p); self._path_input.clear(); self._expr_input.clear()

    def clear(self) -> None: self._path_input.clear(); self._expr_input.clear(); self._list.clear()


class ApiAssertionPanel(QWidget):
    """Mock for compatibility."""
    def __init__(self, parent=None): super().__init__(parent)
    def set_json_path(self, p, v=None): pass
    def clear_all(self): pass
