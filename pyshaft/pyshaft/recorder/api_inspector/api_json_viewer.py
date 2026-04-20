"""PyShaft API Inspector — Interactive JSON response viewer with tree and editable raw views."""

from __future__ import annotations

import json
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
)

from pyshaft.recorder.api_inspector.api_highlighter import ApiSyntaxHighlighter
from pyshaft.recorder.theme import COLORS, FONTS


class ApiJsonViewer(QWidget):
    """Dual-view JSON viewer (Visual Tree + Editable Raw)."""

    path_selected = pyqtSignal(str, object)  # (json_path, value)
    assertion_requested = pyqtSignal(str, object) # (path, data_dict)
    extraction_requested = pyqtSignal(str, object) # (path, value)
    remove_assertion_requested = pyqtSignal(str) # (path)
    data_changed = pyqtSignal(object) # Emitted when raw JSON is edited

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
        if isinstance(v, dict): item.setText(1, f"{{{len(v)} keys}}"); item.setText(2, "object")
        elif isinstance(v, list): item.setText(1, f"[{len(v)} items]"); item.setText(2, "array")
        elif isinstance(v, str): item.setText(1, f'"{v[:50]}"'); item.setText(2, "string"); item.setForeground(1, QColor(COLORS['accent_green']))
        elif isinstance(v, bool): item.setText(1, str(v).lower()); item.setText(2, "bool"); item.setForeground(1, QColor(COLORS['accent_purple']))
        elif isinstance(v, (int, float)): item.setText(1, str(v)); item.setText(2, "number"); item.setForeground(1, QColor(COLORS['accent_orange']))
        elif v is None: item.setText(1, "null"); item.setText(2, "null")

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
        item = self._tree.itemAt(pos)
        if not item: return
        path = item.data(0, Qt.ItemDataRole.UserRole)
        value = item.data(1, Qt.ItemDataRole.UserRole)
        col = self._tree.columnAt(pos.x())

        menu = QMenu()
        menu.setStyleSheet(f"background: {COLORS['bg_medium']}; color: white;")
        
        if col == 0: # Key
            menu.addAction("🔍 Assert Key Exists", lambda: self._emit_assertion(path, "exists"))
            menu.addAction("🗑 Delete Object", lambda: self._delete_node(item))
        else: # Value
            menu.addAction("🎯 Assert Exact", lambda: self._emit_assertion(path, "equals", value))
            menu.addAction("📝 Assert Contains", lambda: self._emit_assertion(path, "contains", value))
            menu.addAction("🔢 Assert Type", lambda: self._emit_assertion(path, "type", type(value).__name__))
            menu.addSeparator()
            menu.addAction("📦 Extract", lambda: self.extraction_requested.emit(path, value))
            menu.addAction("🗑 Remove Value", lambda: self._delete_node(item))
            
        menu.exec(self._tree.viewport().mapToGlobal(pos))

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
