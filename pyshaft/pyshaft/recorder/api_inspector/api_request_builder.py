"""PyShaft API Inspector — Reusable request builder widget (used in tabs)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyshaft.recorder.api_inspector.api_highlighter import ApiSyntaxHighlighter
from pyshaft.recorder.api_inspector.api_models import AuthType, HttpMethod
from pyshaft.recorder.theme import COLORS, FONTS

if TYPE_CHECKING:
    from pyshaft.recorder.api_inspector.api_models import ApiRequestStep


class ApiRequestBuilder(QScrollArea):
    """A standalone request builder widget for a single endpoint."""

    changed = pyqtSignal()

    def __init__(self, step: ApiRequestStep, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.step = step
        self.setWidgetResizable(True)
        self.setStyleSheet(f"QScrollArea {{ border: none; background: {COLORS['bg_dark']}; }}")

        self._build_ui()
        self._load_step(step)

    def _build_ui(self) -> None:
        container = QWidget()
        self.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # ── Unified URL Bar ──
        url_container = QFrame()
        url_container.setObjectName("url_bar_frame")
        url_container.setStyleSheet(f"""
            QFrame#url_bar_frame {{
                background: {COLORS['bg_darkest']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 2px;
            }}
            QFrame#url_bar_frame:focus-within {{
                border-color: {COLORS['accent_purple']};
            }}
        """)
        url_row = QHBoxLayout(url_container)
        url_row.setContentsMargins(4, 4, 4, 4)
        url_row.setSpacing(8)

        self._method_combo = QComboBox()
        for m in HttpMethod:
            self._method_combo.addItem(m.value, m)
        self._method_combo.setFixedWidth(90)
        self._method_combo.setStyleSheet(f"""
            QComboBox {{
                border: none;
                background: {COLORS['bg_hover']};
                border-radius: 4px;
                font-weight: 700;
                color: {COLORS['accent_purple']};
                padding: 6px 8px;
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        self._method_combo.currentIndexChanged.connect(self.changed.emit)
        url_row.addWidget(self._method_combo)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("Enter request URL or endpoint...")
        self._url_input.textChanged.connect(self.changed.emit)
        self._url_input.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background: transparent;
                font-family: {FONTS['family_mono']};
                font-size: 13px;
                color: {COLORS['text_primary']};
                padding: 4px;
            }}
        """)
        url_row.addWidget(self._url_input, 1)
        layout.addWidget(url_container)

        # ── Request Configuration Tabs ──
        self._request_tabs = QTabWidget()
        self._request_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                background: {COLORS['bg_card']};
                margin-top: -1px;
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
                color: {COLORS['accent_purple']};
                border-bottom: 2px solid {COLORS['accent_purple']};
            }}
            QTabBar::tab:hover:!selected {{
                color: {COLORS['text_primary']};
                background: {COLORS['bg_hover']}44;
            }}
        """)

        # Payload tab
        payload_widget = QWidget()
        payload_layout = QVBoxLayout(payload_widget)
        payload_layout.setContentsMargins(8, 8, 8, 8)
        self._payload_input = QPlainTextEdit()
        self._payload_highlighter = ApiSyntaxHighlighter(self._payload_input.document(), mode="json")
        self._payload_input.setPlaceholderText('{\n  "key": "value"\n}')
        self._payload_input.textChanged.connect(self.changed.emit)
        self._payload_input.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {COLORS['bg_darkest']};
                border: none;
                border-radius: 4px;
                font-family: {FONTS['family_mono']};
                font-size: 13px;
                color: {COLORS['text_primary']};
                padding: 12px;
            }}
        """)
        payload_layout.addWidget(self._payload_input)
        self._request_tabs.addTab(payload_widget, "Body")

        # Headers tab
        headers_widget = QWidget()
        headers_layout = QVBoxLayout(headers_widget)
        headers_layout.setContentsMargins(8, 8, 8, 8)
        self._headers_input = QPlainTextEdit()
        self._headers_input.setPlaceholderText('Content-Type: application/json\nX-Custom: value')
        self._headers_input.textChanged.connect(self.changed.emit)
        self._headers_input.setStyleSheet(self._payload_input.styleSheet())
        headers_layout.addWidget(self._headers_input)
        self._request_tabs.addTab(headers_widget, "Headers")

        # Auth tab
        auth_widget = QWidget()
        auth_layout = QVBoxLayout(auth_widget)
        auth_layout.setContentsMargins(16, 16, 16, 16)
        auth_layout.setSpacing(12)
        
        auth_row = QHBoxLayout()
        self._auth_type_combo = QComboBox()
        for at in AuthType:
            self._auth_type_combo.addItem(at.value.replace("_", " ").title(), at)
        self._auth_type_combo.currentIndexChanged.connect(self.changed.emit)
        auth_row.addWidget(QLabel("Type:"), 0)
        auth_row.addWidget(self._auth_type_combo, 1)
        auth_layout.addLayout(auth_row)

        auth_val_row = QHBoxLayout()
        auth_val_row.addWidget(QLabel("Value:"), 0)
        self._auth_value_input = QLineEdit()
        self._auth_value_input.setPlaceholderText("Token or $ENV_VAR")
        self._auth_value_input.textChanged.connect(self.changed.emit)
        auth_val_row.addWidget(self._auth_value_input, 1)
        auth_layout.addLayout(auth_val_row)

        auth_key_row = QHBoxLayout()
        auth_key_row.addWidget(QLabel("Key:"), 0)
        self._auth_key_input = QLineEdit()
        self._auth_key_input.setPlaceholderText("Header name for API key (optional)")
        self._auth_key_input.textChanged.connect(self.changed.emit)
        auth_key_row.addWidget(self._auth_key_input, 1)
        auth_layout.addLayout(auth_key_row)
        auth_layout.addStretch()
        self._request_tabs.addTab(auth_widget, "Auth")

        # Loop tab
        loop_widget = QWidget()
        loop_layout = QVBoxLayout(loop_widget)
        loop_layout.setContentsMargins(16, 16, 16, 16)
        loop_layout.setSpacing(12)
        
        loop_info = QLabel("🔁 Loop over an array variable and inject items into the payload.")
        loop_info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9pt;")
        loop_layout.addWidget(loop_info)

        loop_row1 = QHBoxLayout()
        loop_row1.addWidget(QLabel("Variable:"), 0)
        self._loop_var_input = QLineEdit()
        self._loop_var_input.setPlaceholderText("e.g. user_list")
        self._loop_var_input.textChanged.connect(self.changed.emit)
        loop_row1.addWidget(self._loop_var_input, 1)
        loop_layout.addLayout(loop_row1)

        loop_row2 = QHBoxLayout()
        loop_row2.addWidget(QLabel("Key Path:"), 0)
        self._loop_key_input = QLineEdit()
        self._loop_key_input.setPlaceholderText("JSON key to replace with item")
        self._loop_key_input.textChanged.connect(self.changed.emit)
        loop_row2.addWidget(self._loop_key_input, 1)
        loop_layout.addLayout(loop_row2)
        
        loop_layout.addStretch()
        self._request_tabs.addTab(loop_widget, "Loop")
        layout.addWidget(self._request_tabs)

        # ── Settings & Footer ──
        footer = QFrame()
        footer.setStyleSheet(f"background: {COLORS['bg_dark']}; border-top: 1px solid {COLORS['border']}; border-radius: 4px;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(8, 8, 8, 8)

        footer_layout.addWidget(QLabel("Expect Status:"), 0)
        self._expected_status = QLineEdit("200")
        self._expected_status.setFixedWidth(40)
        self._expected_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._expected_status.textChanged.connect(self.changed.emit)
        footer_layout.addWidget(self._expected_status)

        footer_layout.addSpacing(12)
        footer_layout.addWidget(QLabel("Retry:"), 0)
        self._retry_count = QLineEdit()
        self._retry_count.setPlaceholderText("0")
        self._retry_count.setFixedWidth(30)
        self._retry_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(self._retry_count)
        
        self._retry_mode = QComboBox()
        self._retry_mode.addItems(["all", "timeout", "fail", "status", "exception"])
        self._retry_mode.setFixedWidth(80)
        footer_layout.addWidget(self._retry_mode)
        
        footer_layout.addStretch()
        layout.addWidget(footer)


    def _load_step(self, step: ApiRequestStep) -> None:
        """Populate UI from step data."""
        self.blockSignals(True)
        # Method
        for i in range(self._method_combo.count()):
            if self._method_combo.itemData(i) == step.method:
                self._method_combo.setCurrentIndex(i)
                break

        self._url_input.setText(step.url or step.endpoint)
        self._payload_input.setPlainText(step.payload)
        self._expected_status.setText(str(step.expected_status))

        # Headers
        header_lines = [f"{k}: {v}" for k, v in step.headers.items()]
        self._headers_input.setPlainText("\n".join(header_lines))

        # Auth
        for i in range(self._auth_type_combo.count()):
            if self._auth_type_combo.itemData(i) == step.auth_type:
                self._auth_type_combo.setCurrentIndex(i)
                break
        self._auth_value_input.setText(step.auth_value)
        self._auth_key_input.setText(step.auth_key)

        # Loop
        self._loop_var_input.setText(step.loop_variable)
        self._loop_key_input.setText(step.loop_payload_key)

        # Retry fields
        self._retry_count.setText(str(step.retry_count) if step.retry_count else "")
        self._retry_mode.setCurrentText(step.retry_mode if step.retry_mode else "all")
        self.blockSignals(False)

    def save_to_step(self) -> None:
        """Save UI state back to the model step."""
        self.step.method = self._method_combo.currentData() or HttpMethod.GET
        self.step.url = self._url_input.text().strip()
        self.step.payload = self._payload_input.toPlainText().strip()
        self.step.auth_type = self._auth_type_combo.currentData() or AuthType.NONE
        self.step.auth_value = self._auth_value_input.text().strip()
        self.step.auth_key = self._auth_key_input.text().strip()
        self.step.loop_variable = self._loop_var_input.text().strip()
        self.step.loop_payload_key = self._loop_key_input.text().strip()

        try:
            self.step.expected_status = int(self._expected_status.text().strip())
        except ValueError:
            self.step.expected_status = 200

        self.step.headers = {}
        for line in self._headers_input.toPlainText().strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                self.step.headers[k.strip()] = v.strip()

        # Retry fields
        try:
            self.step.retry_count = int(self._retry_count.text().strip()) if self._retry_count.text().strip() else 0
        except ValueError:
            self.step.retry_count = 0
        self.step.retry_mode = self._retry_mode.currentText()

