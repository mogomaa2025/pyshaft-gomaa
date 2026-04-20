"""PyShaft API Inspector — Explorer dock with hierarchical view and search."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDockWidget,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QMenu,
    QInputDialog,
)

from pyshaft.recorder.api_inspector.api_models import ApiFolder, ApiRequestStep, ApiWorkflow
from pyshaft.recorder.theme import COLORS, FONTS

if TYPE_CHECKING:
    from pyshaft.recorder.api_inspector.api_models import ApiFolder, ApiRequestStep


class ApiExplorerDock(QDockWidget):
    """Explorer dock showing folders and requests."""

    step_selected = pyqtSignal(object)  # ApiRequestStep
    item_deleted = pyqtSignal(bool) # Signal to refresh other docks, bool = refresh_explorer
    item_added = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Explorer", parent)
        self.setObjectName("explorer_dock")
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.setMinimumWidth(220) # Ensure enough space for text
        self._workflow: ApiWorkflow | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Search Bar
        search_layout = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 Search endpoints...")
        self._search_input.textChanged.connect(self._on_search_changed)
        self._search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['bg_darkest']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px 8px;
                color: {COLORS['text_primary']};
            }}
        """)
        search_layout.addWidget(self._search_input, 1)
        
        btn_add_folder = QPushButton("📁+")
        btn_add_folder.setToolTip("Add Root Folder")
        btn_add_folder.clicked.connect(self._on_add_root_folder_clicked)
        btn_add_folder.setStyleSheet("padding: 4px;")
        search_layout.addWidget(btn_add_folder)
        
        layout.addLayout(search_layout)

        # Tree
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(12)
        self._tree.setAnimated(True)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # Enable Drag and Drop
        self._tree.setDragEnabled(True)
        self._tree.setAcceptDrops(True)
        self._tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self._tree.setDropIndicatorShown(True)
        self._tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._tree.dropEvent = self._on_drop_event
        
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {COLORS['bg_dark']};
                border: none;
                font-size: 13px;
                color: {COLORS['text_primary']};
            }}
            QTreeWidget::item {{
                padding: 4px;
            }}
            QTreeWidget::item:selected {{
                background: {COLORS['accent_purple']}33;
                border-left: 2px solid {COLORS['accent_purple']};
            }}
        """)
        layout.addWidget(self._tree)

        self.setWidget(container)

    def _on_drop_event(self, event) -> None:
        """Handle internal drag and drop manually to prevent duplication and sync model."""
        if event.source() != self._tree:
            return

        selected_items = self._tree.selectedItems()
        if not selected_items:
            return
        source_item = selected_items[0]
        
        target_item = self._tree.itemAt(event.position().toPoint())
        indicator = self._tree.dropIndicatorPosition()
        
        # 1. Remove from old position in tree
        old_parent = source_item.parent() or self._tree.invisibleRootItem()
        old_parent.takeChild(old_parent.indexOfChild(source_item))
        
        # 2. Insert into new position in tree
        if not target_item:
            self._tree.invisibleRootItem().addChild(source_item)
        else:
            target_data = target_item.data(0, Qt.ItemDataRole.UserRole)
            if indicator == QTreeWidget.DropIndicatorPosition.OnItem and isinstance(target_data, ApiFolder):
                target_item.addChild(source_item)
                target_item.setExpanded(True)
            elif indicator == QTreeWidget.DropIndicatorPosition.AboveItem:
                parent = target_item.parent() or self._tree.invisibleRootItem()
                parent.insertChild(parent.indexOfChild(target_item), source_item)
            elif indicator == QTreeWidget.DropIndicatorPosition.BelowItem:
                parent = target_item.parent() or self._tree.invisibleRootItem()
                parent.insertChild(parent.indexOfChild(target_item) + 1, source_item)
            else:
                self._tree.invisibleRootItem().addChild(source_item)

        self._tree.setCurrentItem(source_item)
        event.accept()
        
        # 3. Sync model from tree structure
        self._sync_model_from_tree()
        
        # 4. Refresh other docks but skip full explorer rebuild (already correct in tree)
        self.item_deleted.emit(False)

    def _sync_model_from_tree(self) -> None:
        """Rebuild the workflow items list based on the tree structure."""
        if not self._workflow:
            return

        def _collect_items(parent_item: QTreeWidgetItem) -> list:
            items = []
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(data, ApiFolder):
                    data.items = _collect_items(child)
                items.append(data)
            return items

        self._workflow.items = _collect_items(self._tree.invisibleRootItem())

    def set_workflow(self, workflow: ApiWorkflow) -> None:
        """Populate the tree from the workflow."""
        self._workflow = workflow
        self._tree.clear()
        self._populate_recursive(self._tree.invisibleRootItem(), workflow.items)

    def _populate_recursive(self, parent_item: QTreeWidgetItem, items: list[ApiFolder | ApiRequestStep]) -> None:
        for item in items:
            tree_item = QTreeWidgetItem(parent_item)
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item)
            
            if isinstance(item, ApiFolder):
                tree_item.setText(0, item.name)
                tree_item.setForeground(0, Qt.GlobalColor.white)
                tree_item.setIcon(0, self._tree.style().standardIcon(self._tree.style().StandardPixmap.SP_DirIcon))
                tree_item.setFlags(tree_item.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
                self._populate_recursive(tree_item, item.items)
            else:
                method_icon = "🟢" if item.method == "GET" else "🔵" if item.method == "POST" else "🟡"
                tree_item.setText(0, f"{method_icon} {item.name}")
                tree_item.setToolTip(0, f"{item.method} {item.url or item.endpoint}")
                tree_item.setFlags(tree_item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
                # Ensure requests cannot have children dropped into them
                tree_item.setFlags(tree_item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)

    def _on_search_changed(self, text: str) -> None:
        """Filter the tree based on search text."""
        text = text.lower()
        def _filter(item: QTreeWidgetItem) -> bool:
            any_child_visible = False
            for i in range(item.childCount()):
                if _filter(item.child(i)):
                    any_child_visible = True
            
            match = text in item.text(0).lower()
            visible = match or any_child_visible
            item.setHidden(not visible)
            if visible and text:
                item.setExpanded(True)
            return visible

        for i in range(self._tree.topLevelItemCount()):
            _filter(self._tree.topLevelItem(i))

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, ApiRequestStep):
            self.step_selected.emit(data)

    def _show_context_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        menu = QMenu()
        
        if item:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, ApiFolder):
                menu.addAction("➕ Add Request", lambda: self._add_request_to_folder(data))
                menu.addAction("📁 Add Sub-folder", lambda: self._add_subfolder(data))
                menu.addAction("✏ Rename", lambda: self._rename_item(item, data))
            else:
                menu.addAction("✏ Rename", lambda: self._rename_item(item, data))
            
            menu.addSeparator()
            menu.addAction("⬆ Move Up", lambda: self._move_item(item, -1))
            menu.addAction("⬇ Move Down", lambda: self._move_item(item, 1))
            menu.addSeparator()
            menu.addAction("🗑 Delete", lambda: self._delete_item(item, data))
        else:
            menu.addAction("➕ Add Root Request", self._add_root_request)
            menu.addAction("📁 Add Root Folder", self._on_add_root_folder_clicked)
            
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _move_item(self, item: QTreeWidgetItem, delta: int) -> None:
        """Move item up or down in its parent's list."""
        parent = item.parent() or self._tree.invisibleRootItem()
        index = parent.indexOfChild(item)
        new_index = index + delta
        
        if 0 <= new_index < parent.childCount():
            # Move in Tree
            parent.takeChild(index)
            parent.insertChild(new_index, item)
            self._tree.setCurrentItem(item)
            
            # Sync model
            self._sync_model_from_tree()
            self.item_deleted.emit(True)

    def _add_request_to_folder(self, folder: ApiFolder) -> None:
        step = ApiRequestStep(name="New Request")
        folder.items.append(step)
        self.item_deleted.emit(True) 
        self.step_selected.emit(step)
        
    def _add_subfolder(self, folder: ApiFolder) -> None:
        name, ok = QInputDialog.getText(self, "New Folder", "Folder Name:")
        if ok and name:
            new_f = ApiFolder(name=name)
            folder.items.append(new_f)
            self.item_deleted.emit(True)

    def _add_root_request(self) -> None:
        if self._workflow:
            step = ApiRequestStep(name=f"Request {len(self._workflow.all_steps) + 1}")
            self._workflow.items.append(step)
            self.item_deleted.emit(True)
            self.step_selected.emit(step)

    def _on_add_root_folder_clicked(self) -> None:
        if self._workflow:
            name, ok = QInputDialog.getText(self, "New Folder", "Folder Name:")
            if ok and name:
                new_f = ApiFolder(name=name)
                self._workflow.items.append(new_f)
                self.item_deleted.emit(True)

    def _rename_item(self, item: QTreeWidgetItem, data: ApiFolder | ApiRequestStep) -> None:
        name, ok = QInputDialog.getText(self, "Rename", "New Name:", text=data.name)
        if ok and name:
            data.name = name
            self.item_deleted.emit(True)

    def _delete_item(self, tree_item: QTreeWidgetItem, data: ApiFolder | ApiRequestStep) -> None:
        parent_item = tree_item.parent() or self._tree.invisibleRootItem()
        parent_data = parent_item.data(0, Qt.ItemDataRole.UserRole)
        
        if parent_data and isinstance(parent_data, ApiFolder):
            parent_data.items.remove(data)
        elif self._workflow:
            self._workflow.items.remove(data)
            
        self.item_deleted.emit(True)
