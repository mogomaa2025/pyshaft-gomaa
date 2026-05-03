"""PyShaft API Inspector — Interactive JSON response viewer with tree and editable raw views."""

from __future__ import annotations

import json
import re
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QMenu,
    QTabWidget,
    QPushButton,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QApplication,
)

from pyshaft.recorder.api_inspector.api_highlighter import ApiSyntaxHighlighter
from pyshaft.recorder.theme import COLORS, FONTS


# ── Schema Generator Utility ────────────────────────────────────────────

def generate_json_schema(data: Any, title: str = "Response") -> dict:
    """Generate a JSON Schema (draft-07) from a sample JSON value.

    Handles nested objects, arrays (inspects first element for item schema),
    and primitive types.  The result can be stored and used later with
    ``jsonschema.validate`` or PyShaft's ``.assert_schema()`` fluent call.
    """
    schema: dict[str, Any] = {}

    if isinstance(data, dict):
        schema["type"] = "object"
        props: dict[str, Any] = {}
        required: list[str] = []
        for k, v in data.items():
            props[k] = generate_json_schema(v, title=k)
            required.append(k)
        schema["properties"] = props
        if required:
            schema["required"] = required
    elif isinstance(data, list):
        schema["type"] = "array"
        if data:
            # Use first element as representative schema
            schema["items"] = generate_json_schema(data[0], title="item")
        else:
            schema["items"] = {}
    elif isinstance(data, bool):
        schema["type"] = "boolean"
    elif isinstance(data, int):
        schema["type"] = "integer"
    elif isinstance(data, float):
        schema["type"] = "number"
    elif isinstance(data, str):
        schema["type"] = "string"
    elif data is None:
        schema["type"] = "null"
    else:
        schema["type"] = "string"

    return schema


def build_full_schema(data: Any, title: str = "Response") -> dict:
    """Wrap ``generate_json_schema`` with draft-07 meta-information."""
    schema = generate_json_schema(data, title=title)
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["title"] = title
    return schema


# ── Schema Viewer Dialog ─────────────────────────────────────────────────

class SchemaViewerDialog(QDialog):
    """Modal dialog that shows the generated JSON Schema with copy-to-clipboard."""

    def __init__(self, schema: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Generated JSON Schema")
        self.setMinimumSize(600, 500)
        self.setStyleSheet(f"background: {COLORS['bg_dark']}; color: {COLORS['text_primary']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("📐 JSON SCHEMA")
        header.setStyleSheet(f"font-weight: 800; font-size: 10pt; color: {COLORS['accent_purple']}; letter-spacing: 1px;")
        layout.addWidget(header)

        self._editor = QTextEdit()
        self._editor.setReadOnly(True)
        self._schema_text = json.dumps(schema, indent=2)
        self._editor.setPlainText(self._schema_text)
        self._highlighter = ApiSyntaxHighlighter(self._editor.document(), mode="json")
        self._editor.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['bg_darkest']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                color: {COLORS['text_primary']};
                font-family: {FONTS['family_mono']};
                font-size: 13px;
                padding: 12px;
            }}
        """)
        layout.addWidget(self._editor)

        btn_row = QHBoxLayout()
        btn_copy = QPushButton("📋 Copy to Clipboard")
        btn_copy.setStyleSheet(f"background: {COLORS['accent_purple']}22; color: {COLORS['accent_purple']}; font-weight: 600; padding: 10px 20px; border-radius: 6px;")
        btn_copy.clicked.connect(self._copy)
        btn_row.addWidget(btn_copy)

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet(f"background: {COLORS['bg_hover']}; color: {COLORS['text_primary']}; padding: 10px 20px; border-radius: 6px;")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _copy(self) -> None:
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self._schema_text)


# ── JSON Viewer Widget ───────────────────────────────────────────────────

class ApiJsonViewer(QWidget):
    """Dual-view JSON viewer (Visual Tree + Editable Raw)."""

    path_selected = pyqtSignal(str, object)  # (json_path, value)
    assertion_requested = pyqtSignal(str, object) # (path, data_dict)
    extraction_requested = pyqtSignal(str, object) # (path, value)
    remove_assertion_requested = pyqtSignal(str) # (path)
    data_changed = pyqtSignal(object) # Emitted when raw JSON is edited
    schema_assertion_requested = pyqtSignal(str, str)  # (path, schema_json_str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._raw_data: Any = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: {COLORS['bg_dark']};
            }}
            QTabBar::tab {{
                background: transparent;
                padding: 10px 20px;
                font-size: 11px;
                font-weight: 600;
                color: {COLORS['text_muted']};
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QTabBar::tab:selected {{
                color: {COLORS['accent_green']};
                border-bottom: 2px solid {COLORS['accent_green']};
            }}
        """)

        # ── Tab 1: Visual Tree ──
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(12, 12, 12, 12)
        tree_layout.setSpacing(10)

        # Tree Toolbar
        tree_tools = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Filter response keys or values...")
        self._search_input.textChanged.connect(self._on_search_changed)
        self._search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['bg_darkest']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {COLORS['accent_green']}; }}
        """)
        tree_tools.addWidget(self._search_input, 1)

        btn_expand = QPushButton("↔")
        btn_expand.setFixedSize(28, 28); btn_expand.setToolTip("Expand All")
        btn_expand.clicked.connect(lambda: self._tree.expandAll())
        tree_tools.addWidget(btn_expand)

        btn_collapse = QPushButton("↕")
        btn_collapse.setFixedSize(28, 28); btn_collapse.setToolTip("Collapse All")
        btn_collapse.clicked.connect(lambda: self._tree.collapseAll())
        tree_tools.addWidget(btn_collapse)
        tree_layout.addLayout(tree_tools)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Key", "Value", "Type"])
        self._tree.setColumnWidth(0, 200)
        self._tree.setAlternatingRowColors(True)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.setStyleSheet(self._tree_style())
        tree_layout.addWidget(self._tree)

        self._path_label = QLabel("")
        self._path_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-family: {FONTS['family_mono']}; font-size: 9pt; padding-top: 4px;")
        tree_layout.addWidget(self._path_label)

        self._tabs.addTab(tree_container, "Preview")

        # ── Tab 2: Raw Editable JSON ──
        raw_container = QWidget()
        raw_layout = QVBoxLayout(raw_container)
        raw_layout.setContentsMargins(12, 12, 12, 12)
        raw_layout.setSpacing(10)

        self._raw_edit = QTextEdit()
        self._highlighter = ApiSyntaxHighlighter(self._raw_edit.document(), mode="json")
        self._raw_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['bg_darkest']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                color: {COLORS['text_primary']};
                font-family: {FONTS['family_mono']};
                font-size: 13px;
                padding: 12px;
            }}
        """)
        raw_layout.addWidget(self._raw_edit)

        btn_apply = QPushButton("Apply Local Changes")
        btn_apply.setStyleSheet(f"background: {COLORS['bg_hover']}; color: {COLORS['text_primary']}; font-weight: 600; padding: 10px; border-radius: 6px;")
        btn_apply.clicked.connect(self._apply_raw_changes)
        raw_layout.addWidget(btn_apply)

        self._tabs.addTab(raw_container, "Raw")

        layout.addWidget(self._tabs)

    def _tree_style(self) -> str:
        return f"""
            QTreeWidget {{ background: {COLORS['bg_darkest']}; border: none; color: {COLORS['text_primary']}; }}
            QTreeWidget::item:selected {{ background: {COLORS['accent_purple']}44; }}
            QHeaderView::section {{ background: {COLORS['bg_dark']}; color: {COLORS['text_muted']}; border: none; padding: 4px; }}
        """

    def set_data(self, data: Any) -> None:
        """Update both views with new data."""
        self._raw_data = data
        self._tree.clear()
        self._path_label.setText("")

        # 1. Update Raw Editor
        if data is not None:
            self._raw_edit.setPlainText(json.dumps(data, indent=2))
        else:
            self._raw_edit.setPlainText("")

        # 2. Update Tree
        if isinstance(data, (dict, list)):
            self._populate_tree(self._tree.invisibleRootItem(), data, "$")
            self._tree.expandToDepth(1)
        elif data is not None:
            # Fallback for non-JSON
            item = QTreeWidgetItem(self._tree)
            item.setText(0, "Response")
            item.setText(1, str(data))

    def _populate_tree(self, parent: QTreeWidgetItem, data: Any, path: str) -> None:
        if isinstance(data, dict):
            for k, v in data.items():
                child_path = f"{path}.{k}" if path != "$" else f"$.{k}"
                item = QTreeWidgetItem(parent)
                item.setData(0, Qt.ItemDataRole.UserRole, child_path)
                item.setData(1, Qt.ItemDataRole.UserRole, v)
                item.setText(0, str(k))
                self._set_value_display(item, v)
                if isinstance(v, (dict, list)): self._populate_tree(item, v, child_path)
        elif isinstance(data, list):
            for i, v in enumerate(data):
                child_path = f"{path}[{i}]"
                item = QTreeWidgetItem(parent)
                item.setData(0, Qt.ItemDataRole.UserRole, child_path)
                item.setData(1, Qt.ItemDataRole.UserRole, v)
                item.setText(0, f"[{i}]")
                self._set_value_display(item, v)
                if isinstance(v, (dict, list)): self._populate_tree(item, v, child_path)

    def _set_value_display(self, item: QTreeWidgetItem, v: Any) -> None:
        if isinstance(v, dict): 
            item.setText(1, f"{{{len(v)} keys}}")
            item.setText(2, "object")
        elif isinstance(v, list): 
            item.setText(1, f"[{len(v)} items]")
            item.setText(2, "array")
        elif isinstance(v, str): 
            item.setText(1, f'"{v[:50]}"')
            # Detect semantic types for better assertions
            t = "string"
            if re.match(r"^\d{4}-\d{2}-\d{2}", v): t = "date"
            elif re.match(r"^[a-fA-F0-9-]{36}$", v): t = "uuid"
            item.setText(2, t)
            item.setForeground(1, QColor(COLORS['accent_green']))
        elif isinstance(v, bool): 
            item.setText(1, "True" if v else "False")
            item.setText(2, "bool")
            item.setForeground(1, QColor(COLORS['accent_purple']))
        elif isinstance(v, (int, float)): 
            item.setText(1, str(v))
            item.setText(2, "number")
            item.setForeground(1, QColor(COLORS['accent_orange']))
        elif v is None: 
            item.setText(1, "None")
            item.setText(2, "null")

    def _on_search_changed(self, text: str) -> None:
        """Filter items and highlight matches."""
        text = text.lower()
        def _process(item: QTreeWidgetItem) -> bool:
            # Check key or value
            match = text in item.text(0).lower() or text in item.text(1).lower()
            
            # Highlight matching item
            if text and match:
                item.setBackground(0, QColor(COLORS['accent_green'] + "44"))
                item.setBackground(1, QColor(COLORS['accent_green'] + "44"))
            else:
                item.setBackground(0, Qt.GlobalColor.transparent)
                item.setBackground(1, Qt.GlobalColor.transparent)

            any_child_visible = False
            for i in range(item.childCount()):
                if _process(item.child(i)): any_child_visible = True
            
            visible = not text or match or any_child_visible
            item.setHidden(not visible)
            if text and visible: item.setExpanded(True)
            return visible

        for i in range(self._tree.topLevelItemCount()):
            _process(self._tree.topLevelItem(i))

    def _apply_raw_changes(self) -> None:
        """Parse edited raw JSON and sync to tree."""
        try:
            new_data = json.loads(self._raw_edit.toPlainText())
            self.set_data(new_data)
            self.data_changed.emit(new_data)
        except Exception as e:
            QMessageBox.critical(self, "Invalid JSON", f"Failed to parse JSON:\n{e}")

    def _show_context_menu(self, pos) -> None:
        import re
        item = self._tree.itemAt(pos)
        if not item: return
        path = item.data(0, Qt.ItemDataRole.UserRole)
        value = item.data(1, Qt.ItemDataRole.UserRole)
        col = self._tree.columnAt(pos.x())

        menu = QMenu()
        menu.setStyleSheet(f"background: {COLORS['bg_medium']}; color: white;")
        
        if col == 0: # Key
            menu.addAction("🔍 Assert Key Exists", lambda: self._emit_assertion(path, "exists"))
            
            # Smart iteration helper: if item is inside an array, allow asserting for ALL items
            if "[" in path and "]" in path:
                # Replace [0], [1] etc with [*] for the immediate parent array
                iter_path = re.sub(r"\[\d+\]", "[*]", path)
                menu.addAction(f"🔄 Assert for ALL in array", lambda: self._emit_assertion(iter_path, "equals", value))
                
            menu.addAction("🗑 Delete Object", lambda: self._delete_node(item))
        else: # Value
            menu.addAction("🎯 Assert Exact", lambda: self._emit_assertion(path, "equals", value))
            menu.addAction("📝 Assert Contains", lambda: self._emit_assertion(path, "contains", value))
            
            # Deep equal options for objects
            if isinstance(value, dict):
                menu.addSeparator()
                menu.addAction("🔀 Assert Deep Equal", lambda: self._emit_assertion(path, "deep_equals", value))
                menu.addAction("🔀 Assert Deep Contains", lambda: self._emit_assertion(path, "deep_contains", value))
                menu.addSeparator()
            
            # Detect type name including semantic ones
            v_type = item.text(2) # Use the text we set in _set_value_display
            menu.addAction(f"🔢 Assert Type ({v_type})", lambda: self._emit_assertion(path, "type", v_type))
            
            menu.addSeparator()
            if isinstance(value, (dict, list)):
                menu.addAction("📐 Assert Schema", lambda p=path, v=value: self._assert_schema(p, v))
                menu.addSeparator()
                
            menu.addAction("📦 Extract", lambda: self.extraction_requested.emit(path, value))
            
            if "[" in path and "]" in path:
                # Replace last array index [N] with [last] - handles paths like data[0].name or data.items[2].id
                # Match [...] that is followed by either end of string or another key (like .name or /key)
                last_path = re.sub(r"\[(\d+)\](?=\.|$)", "[last]", path)
                menu.addAction("📦 Extract LAST", lambda: self.extraction_requested.emit(last_path, value))
                menu.addAction("🎯 Assert LAST", lambda: self._emit_assertion(last_path, "equals", value))

            menu.addAction("🗑 Remove Value", lambda: self._delete_node(item))

        # Root-level schema for entire response (always available)
        menu.addSeparator()
        if self._raw_data and isinstance(self._raw_data, (dict, list)):
            menu.addAction("📐 Assert Full Response Schema", lambda: self._assert_schema("$", self._raw_data))
            menu.addAction("📐 View Full Response Schema", lambda: self._view_schema(self._raw_data))
            
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _assert_schema(self, path: str, value: Any) -> None:
        """Generate a schema from the value and emit as a schema assertion."""
        schema = build_full_schema(value, title=path)
        schema_str = json.dumps(schema, indent=2)
        self.schema_assertion_requested.emit(path, schema_str)

    def _view_schema(self, value: Any) -> None:
        """Open a dialog showing the generated schema."""
        schema = build_full_schema(value)
        dialog = SchemaViewerDialog(schema, parent=self)
        dialog.exec()

    def _delete_node(self, item: QTreeWidgetItem) -> None:
        """Remove a node from the tree and update raw data."""
        parent = item.parent() or self._tree.invisibleRootItem()
        parent.removeChild(item)
        # We don't necessarily update the step model here, but the visual tree reflects the change.

    def _emit_assertion(self, path: str, mode: str, val: Any = None) -> None:
        self.assertion_requested.emit(path, {"mode": mode, "value": val})

    def _on_item_clicked(self, item: QTreeWidgetItem, col: int) -> None:
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path:
            self._path_label.setText(path)
            self.path_selected.emit(path, item.data(1, Qt.ItemDataRole.UserRole))
