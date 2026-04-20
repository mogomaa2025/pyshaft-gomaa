"""PyShaft Recorder — Workflow Diagram View.

Visual node-based diagram of test steps with drag-and-drop.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QBrush, QPainterPath,
    QLinearGradient, QRadialGradient,
)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsPathItem,
    QGraphicsEllipseItem, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QMenu, QGraphicsDropShadowEffect,
)

from pyshaft.recorder.models import RecordedStep, RecordingSession
from pyshaft.recorder.theme import COLORS, FONTS, ICONS


# Node dimensions
NODE_W = 260
NODE_H = 75
NODE_SPACING_Y = 100
NODE_SPACING_X = 50
CONNECTOR_ARROW_SIZE = 8


class StepNode(QGraphicsRectItem):
    """A draggable node representing a test step in the workflow diagram."""

    def __init__(self, step: RecordedStep, index: int, parent=None):
        super().__init__(0, 0, NODE_W, NODE_H, parent)
        self.step = step
        self.step_index = index
        self._setup_style()
        self._setup_content()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAcceptHoverEvents(True)
        self.edges_in = []
        self.edges_out = []

    def itemChange(self, change, value):
        from PyQt6.QtWidgets import QGraphicsItem
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in getattr(self, "edges_in", []):
                if hasattr(edge, "_update_path"):
                    edge._update_path()
            for edge in getattr(self, "edges_out", []):
                if hasattr(edge, "_update_path"):
                    edge._update_path()
        return super().itemChange(change, value)

    def _setup_style(self):
        cat_colors = {
            "action": QColor(COLORS["step_action"]),
            "assert": QColor(COLORS["step_assert"]),
            "nav": QColor(COLORS["step_nav"]),
            "wait": QColor(COLORS["step_wait"]),
        }
        color = cat_colors.get(self.step.category, QColor(COLORS["step_action"]))

        # Rounded rectangle
        self.setBrush(QBrush(QColor(COLORS["bg_card"])))
        self.setPen(QPen(color, 2))

        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

    def _setup_content(self):
        cat_colors = {
            "action": COLORS["step_action"],
            "assert": COLORS["step_assert"],
            "nav": COLORS["step_nav"],
            "wait": COLORS["step_wait"],
        }
        color = cat_colors.get(self.step.category, COLORS["step_action"])

        # Index badge
        badge = QGraphicsEllipseItem(6, 6, 20, 20, self)
        badge.setBrush(QBrush(QColor(color)))
        badge.setPen(QPen(Qt.PenStyle.NoPen))

        badge_text = QGraphicsTextItem(str(self.step_index + 1), self)
        badge_text.setDefaultTextColor(QColor(COLORS["bg_darkest"]))
        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        badge_text.setFont(font)
        # Center in badge
        br = badge_text.boundingRect()
        badge_text.setPos(16 - br.width() / 2, 16 - br.height() / 2)

        # Action name
        action_text = QGraphicsTextItem(f"{self.step.icon} {self.step.action}", self)
        action_text.setDefaultTextColor(QColor(color))
        action_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        action_text.setFont(action_font)
        action_text.setPos(32, 6)

        # Detail text (with wrap)
        detail = self.step.display_label
        detail_text = QGraphicsTextItem(detail, self)
        detail_text.setTextWidth(NODE_W - 40)
        detail_text.setDefaultTextColor(QColor(COLORS["text_secondary"]))
        detail_font = QFont("Cascadia Code", 8)
        detail_text.setFont(detail_font)
        detail_text.setPos(32, 28)

    def paint(self, painter: QPainter, option, widget=None):
        """Custom paint with rounded corners."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)

        # Fill
        painter.fillPath(path, self.brush())

        # Border
        pen = self.pen()
        if self.isSelected():
            pen = QPen(QColor(COLORS["accent_purple"]), 3)
        painter.setPen(pen)
        painter.drawPath(path)

    def hoverEnterEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setPen(QPen(QColor(COLORS["accent_purple"]), 2))
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        cat_colors = {
            "action": QColor(COLORS["step_action"]),
            "assert": QColor(COLORS["step_assert"]),
            "nav": QColor(COLORS["step_nav"]),
            "wait": QColor(COLORS["step_wait"]),
        }
        color = cat_colors.get(self.step.category, QColor(COLORS["step_action"]))
        self.setPen(QPen(color, 2))
        self.update()
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        scene = self.scene()
        if hasattr(scene, "step_edited"):
            scene.step_edited.emit(self.step.id)
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['bg_medium']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 4px;
                color: {COLORS['text_primary']};
            }}
            QMenu::item {{
                padding: 8px 24px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['accent_purple']};
            }}
        """)

        remove_action = menu.addAction("✕  Remove Step")
        edit_action = menu.addAction("✎  Edit Step")

        action = menu.exec(event.screenPos())
        if action == remove_action:
            # Notify parent scene
            scene = self.scene()
            if isinstance(scene, WorkflowScene):
                scene.step_removed.emit(self.step.id)
        elif action == edit_action:
            scene = self.scene()
            if isinstance(scene, WorkflowScene):
                scene.step_edited.emit(self.step.id)


class ConnectorLine(QGraphicsPathItem):
    """An arrow connecting two step nodes."""

    def __init__(self, start_node: StepNode, end_node: StepNode, parent=None):
        super().__init__(parent)
        self.start_node = start_node
        self.end_node = end_node
        self._update_path()

        pen = QPen(QColor(COLORS["border_light"]), 2)
        pen.setStyle(Qt.PenStyle.SolidLine)
        self.setPen(pen)

    def _update_path(self):
        start = self.start_node.sceneBoundingRect()
        end = self.end_node.sceneBoundingRect()

        sx = start.center().x()
        sy = start.bottom()
        ex = end.center().x()
        ey = end.top()

        path = QPainterPath()
        path.moveTo(sx, sy)

        # Smooth bezier curve
        mid_y = (sy + ey) / 2
        path.cubicTo(sx, mid_y, ex, mid_y, ex, ey)

        self.setPath(path)

        # Draw arrowhead
        self._draw_arrow(ex, ey)

    def _draw_arrow(self, x, y):
        """Draw a simple arrowhead at the endpoint."""
        # Arrow is part of the main path paint
        pass  # Arrowhead drawn in paint

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw arrowhead at end
        end = self.end_node.sceneBoundingRect()
        ex = end.center().x()
        ey = end.top()

        arrow_size = CONNECTOR_ARROW_SIZE
        painter.setBrush(QBrush(QColor(COLORS["border_light"])))
        painter.setPen(QPen(Qt.PenStyle.NoPen))

        path = QPainterPath()
        path.moveTo(ex, ey)
        path.lineTo(ex - arrow_size / 2, ey - arrow_size)
        path.lineTo(ex + arrow_size / 2, ey - arrow_size)
        path.closeSubpath()
        painter.drawPath(path)


class WorkflowScene(QGraphicsScene):
    """Scene managing step nodes and connector lines."""

    step_removed = pyqtSignal(str)   # step_id
    step_edited = pyqtSignal(str)    # step_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QBrush(QColor(COLORS["bg_darkest"])))
        self._nodes: list[StepNode] = []
        self._connectors: list[ConnectorLine] = []

    def build_from_session(self, session: RecordingSession):
        """Rebuild the diagram from a recording session."""
        self.clear()
        self._nodes.clear()
        self._connectors.clear()

        if not session.steps:
            # Show empty state text
            text = self.addText(
                "No steps recorded yet.\nStart recording to see the workflow diagram.",
                QFont("Segoe UI", 12)
            )
            text.setDefaultTextColor(QColor(COLORS["text_muted"]))
            text.setPos(50, 80)
            return

        # Create nodes
        x = 50
        y = 30
        for i, step in enumerate(session.steps):
            node = StepNode(step, i)
            node.setPos(x, y)
            self.addItem(node)
            self._nodes.append(node)
            y += NODE_SPACING_Y

        # Create connectors
        for i in range(len(self._nodes) - 1):
            connector = ConnectorLine(self._nodes[i], self._nodes[i + 1])
            self.addItem(connector)
            self._connectors.append(connector)
            self._nodes[i].edges_out.append(connector)
            self._nodes[i + 1].edges_in.append(connector)

        # Set scene rect with padding
        total_height = len(session.steps) * NODE_SPACING_Y + 60
        self.setSceneRect(0, 0, NODE_W + 100, max(total_height, 400))


class WorkflowView(QWidget):
    """Widget containing the workflow diagram with zoom controls."""

    step_removed = pyqtSignal(str)   # step_id
    step_edited = pyqtSignal(str)    # step_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QFrame()
        toolbar.setObjectName("toolbar_frame")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)

        title = QLabel(f"{COLORS.get('workflow', '🔀')} Workflow Diagram")
        title.setStyleSheet(f"font-weight: 600; color: {COLORS['text_secondary']};")
        toolbar_layout.addWidget(title)
        toolbar_layout.addStretch()

        # Zoom controls
        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setFixedSize(28, 28)
        zoom_out_btn.clicked.connect(self._zoom_out)
        toolbar_layout.addWidget(zoom_out_btn)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: {FONTS['size_sm']};")
        toolbar_layout.addWidget(self._zoom_label)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(28, 28)
        zoom_in_btn.clicked.connect(self._zoom_in)
        toolbar_layout.addWidget(zoom_in_btn)

        fit_btn = QPushButton("Fit")
        fit_btn.setFixedWidth(40)
        fit_btn.clicked.connect(self._zoom_fit)
        toolbar_layout.addWidget(fit_btn)

        toolbar_layout.addSpacing(12)

        export_png_btn = QPushButton(f"{ICONS.get('camera', '📷')} PNG")
        export_png_btn.setToolTip("Export diagram as PNG")
        export_png_btn.clicked.connect(self._export_png)
        toolbar_layout.addWidget(export_png_btn)

        export_uml_btn = QPushButton(f"{ICONS.get('text', '📄')} UML")
        export_uml_btn.setToolTip("Export diagram as PlantUML")
        export_uml_btn.clicked.connect(self._export_uml)
        toolbar_layout.addWidget(export_uml_btn)

        layout.addWidget(toolbar)

        # Session tracking for export
        self._current_session = None

        # Graphics view
        self._scene = WorkflowScene()
        self._scene.step_removed.connect(self.step_removed.emit)
        self._scene.step_edited.connect(self.step_edited.emit)

        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setStyleSheet(f"border: none; background-color: {COLORS['bg_darkest']};")
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(self._view)

        self._zoom_level = 1.0

    def build_from_session(self, session: RecordingSession):
        """Rebuild the workflow diagram from the session."""
        self._current_session = session
        self._scene.build_from_session(session)
        self._zoom_fit()

    def _export_png(self):
        """Render the QGraphicsScene perfectly into a PNG map."""
        if not self._current_session or not self._current_session.steps:
            return
            
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from pyshaft.recorder.io_manager import IOManager
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Diagram to PNG",
            str(IOManager.get_recordings_dir() / f"{self._current_session.name}_workflow.png"),
            "PNG Images (*.png)"
        )
        if not path:
            return

        from PyQt6.QtGui import QImage, QPainter
        rect = self._scene.sceneRect()
        if rect.isEmpty():
            return
            
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._scene.render(painter)
        painter.end()
        image.save(path)

    def _export_uml(self):
        """Parse steps into PlantUML and export."""
        if not self._current_session or not self._current_session.steps:
            return
            
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from pyshaft.recorder.io_manager import IOManager
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Diagram to PlantUML",
            str(IOManager.get_recordings_dir() / f"{self._current_session.name}_workflow.puml"),
            "PlantUML Files (*.puml *.txt)"
        )
        if not path:
            return

        lines = [
            "@startuml",
            f"title {self._current_session.name} Workflow",
            "actor Tester",
            "participant App"
        ]
        
        for step in self._current_session.steps:
            action = step.action
            display = step.display_label.replace('"', "'")
            
            if action.startswith("assert"):
                lines.append(f"Tester -> App: Verify [{display}]")
                lines.append(f"App --> Tester: State Match")
            elif action in ("wait", "sleep"):
                lines.append(f"Tester -> App: Wait ({display})")
            else:
                lines.append(f"Tester -> App: Action [{display}]")
                
        lines.append("@enduml")
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\\n".join(lines))
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to save UML:\\n{e}")

    def _zoom_in(self):
        self._zoom_level = min(self._zoom_level * 1.2, 3.0)
        self._apply_zoom()

    def _zoom_out(self):
        self._zoom_level = max(self._zoom_level / 1.2, 0.3)
        self._apply_zoom()

    def _zoom_fit(self):
        self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_level = 1.0
        self._zoom_label.setText("Fit")

    def _apply_zoom(self):
        self._view.resetTransform()
        self._view.scale(self._zoom_level, self._zoom_level)
        self._zoom_label.setText(f"{int(self._zoom_level * 100)}%")
