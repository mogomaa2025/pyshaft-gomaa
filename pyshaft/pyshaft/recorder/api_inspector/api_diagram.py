"""PyShaft API Inspector — Interactive workflow diagram."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPen, QPainter, QPainterPath, QFont
from PyQt6.QtWidgets import (
    QDockWidget,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QVBoxLayout,
    QWidget,
)

from pyshaft.recorder.theme import COLORS, FONTS

if TYPE_CHECKING:
    from pyshaft.recorder.api_inspector.api_models import ApiRequestStep, ApiWorkflow


class StepNode(QGraphicsRectItem):
    """Representing an API Step in the diagram."""

    def __init__(self, step: ApiRequestStep, x: float, y: float, dock: ApiDiagramDock) -> None:
        super().__init__(0, 0, 200, 90)
        self.step = step
        self.dock = dock
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setBrush(QBrush(QColor(COLORS['bg_card'])))
        self.setPen(QPen(QColor(COLORS['border']), 1))

        # Method badge
        method = step.method.value
        badge_color = "#4CAF50" if method == "GET" else "#2196F3" if method == "POST" else "#FFC107"

        self.name_text = QGraphicsTextItem(self)
        self.name_text.setHtml(f"<div style='color: {COLORS['text_primary']}; font-family: sans-serif; font-size: 11pt;'><b>{step.name}</b></div>")
        self.name_text.setPos(5, 5)
        self.name_text.setTextWidth(190)

        self.method_text = QGraphicsTextItem(self)
        self.method_text.setHtml(f"<b style='color: {badge_color}; font-size: 10pt;'>{method}</b>")
        self.method_text.setPos(5, 35)
        
        # IO Labels
        self._build_io_labels()

    def _build_io_labels(self) -> None:
        # Inputs (Left side)
        import re
        var_pattern = re.compile(r"\{\{([^}]+)\}\}")
        content = f"{self.step.url} {self.step.payload} {str(self.step.headers)}"
        inputs = set(var_pattern.findall(content))
        
        y = 5
        # ── Loop / Data Driven ──
        if self.step.loop_variable:
            label = QGraphicsTextItem(f"🔁 {self.step.loop_variable}", self)
            label.setDefaultTextColor(QColor(COLORS['accent_purple']))
            f = label.font(); f.setPointSize(8); f.setBold(True); label.setFont(f)
            label.setPos(-90, y); y += 18

        # ── Regular Variable Inputs ──
        for inp in inputs:
            label = QGraphicsTextItem(f"⇥ {inp}", self)
            label.setDefaultTextColor(QColor(COLORS['text_secondary']))
            f = label.font(); f.setPointSize(8); label.setFont(f)
            label.setPos(-80, y); y += 15

        # Outputs (Right side)
        y = 5
        for ext in self.step.extractions:
            label = QGraphicsTextItem(f"{ext.variable_name} ↦", self)
            label.setDefaultTextColor(QColor(COLORS['accent_orange']))
            f = label.font(); f.setPointSize(8); label.setFont(f)
            label.setPos(205, y); y += 15
        
        # ── Assertion Dependencies (Bottom) ──
        if self.step.assertions:
            y = 70
            label = QGraphicsTextItem(f"✅ {len(self.step.assertions)} Assertions", self)
            label.setDefaultTextColor(QColor(COLORS['accent_green']))
            f = label.font(); f.setPointSize(7); label.setFont(f)
            label.setPos(5, y)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.dock.step_selected.emit(self.step)

    def paint(self, painter: QPainter, option, widget) -> None:
        if self.isSelected():
            self.setPen(QPen(QColor(COLORS['accent_purple']), 3))
        else:
            self.setPen(QPen(QColor(COLORS['border']), 1))
        super().paint(painter, option, widget)


class DependencyArrow(QGraphicsPathItem):
    """Arrow showing data dependency between steps."""

    def __init__(self, start_item: StepNode, end_item: StepNode, var_name: str) -> None:
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.var_name = var_name
        self.setPen(QPen(QColor(COLORS['accent_purple']), 2, Qt.PenStyle.DashLine))
        self._update_path()

    def _update_path(self) -> None:
        start_pos = self.start_item.scenePos() + QPointF(200, 45)
        end_pos = self.end_item.scenePos() + QPointF(0, 45)
        
        path = QPainterPath()
        path.moveTo(start_pos)
        cp1 = QPointF(start_pos.x() + 80, start_pos.y())
        cp2 = QPointF(end_pos.x() - 80, end_pos.y())
        path.cubicTo(cp1, cp2, end_pos)
        self.setPath(path)


class ApiDiagramDock(QDockWidget):
    """Diagram view for visual workflow analysis."""

    step_selected = pyqtSignal(object)  # ApiRequestStep

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Workflow Map", parent)
        self.setObjectName("diagram_dock")
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self._build_ui()

    def _build_ui(self) -> None:
        self._scene = QGraphicsScene()
        self._scene.setBackgroundBrush(QBrush(QColor(COLORS['bg_darkest'])))
        
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)
        self.setWidget(container)

    def update_diagram(self, workflow: ApiWorkflow) -> None:
        """Analyze workflow and rebuild diagram."""
        self._scene.clear()
        
        steps = workflow.all_steps
        nodes: dict[str, StepNode] = {}
        
        # Layout steps in a column for now
        for i, step in enumerate(steps):
            node = StepNode(step, 100, 100 + i * 150, self)
            self._scene.addItem(node)
            nodes[step.name] = node

        # Find dependencies
        producers: dict[str, ApiRequestStep] = {}
        for step in steps:
            for ext in step.extractions:
                producers[ext.variable_name] = step
        
        var_pattern = re.compile(r"\{\{([^}]+)\}\}")
        
        for consumer_step in steps:
            content = f"{consumer_step.url} {consumer_step.payload} {str(consumer_step.headers)}"
            vars_used = set(var_pattern.findall(content))
            
            for var in vars_used:
                if var in producers:
                    producer_step = producers[var]
                    if producer_step != consumer_step:
                        p_node = nodes.get(producer_step.name)
                        c_node = nodes.get(consumer_step.name)
                        if p_node and c_node:
                            arrow = DependencyArrow(p_node, c_node, var)
                            self._scene.addItem(arrow)
