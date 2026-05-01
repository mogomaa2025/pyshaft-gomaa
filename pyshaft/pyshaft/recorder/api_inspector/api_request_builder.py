"""PyShaft API Inspector — Reusable request builder widget (used in tabs)."""

from __future__ import annotations

import base64
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
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
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

        # ── Params tab (Query Params + Base64 Encoder) ──
        params_widget = QWidget()
        params_layout = QVBoxLayout(params_widget)
        params_layout.setContentsMargins(8, 8, 8, 8)
        params_layout.setSpacing(12)

        # ── Section: Plain Query Params ──
        qp_label = QLabel("🔗 Query Parameters")
        qp_label.setStyleSheet(f"font-weight: 700; font-size: 9pt; color: {COLORS['accent_purple']}; letter-spacing: 0.5px;")
        params_layout.addWidget(qp_label)

        qp_info = QLabel("Key/value pairs appended to the URL as ?key=value&...")
        qp_info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 8pt;")
        params_layout.addWidget(qp_info)

        self._query_params_table = QTableWidget(0, 2)
        self._query_params_table.setHorizontalHeaderLabels(["Key", "Value"])
        self._query_params_table.horizontalHeader().setStretchLastSection(True)
        self._query_params_table.setStyleSheet(f"""
            QTableWidget {{
                background: {COLORS['bg_darkest']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text_primary']};
                gridline-color: {COLORS['border']};
                font-size: 11px;
            }}
            QHeaderView::section {{
                background: {COLORS['bg_dark']};
                color: {COLORS['text_muted']};
                border: none;
                padding: 6px;
                font-weight: 600;
                font-size: 9pt;
            }}
            QTableWidget::item:selected {{
                background: {COLORS['accent_purple']}33;
            }}
        """)
        self._query_params_table.setMaximumHeight(140)
        self._query_params_table.itemChanged.connect(lambda: self.changed.emit())
        params_layout.addWidget(self._query_params_table)

        qp_btn_row = QHBoxLayout()
        btn_add_qp = QPushButton("➕ Add Row")
        btn_add_qp.setStyleSheet(f"background: {COLORS['bg_hover']}; color: {COLORS['text_primary']}; border: none; padding: 4px 10px; border-radius: 4px;")
        btn_add_qp.clicked.connect(self._add_query_param_row)
        btn_del_qp = QPushButton("🗑 Remove Row")
        btn_del_qp.setStyleSheet(f"background: {COLORS['bg_hover']}; color: {COLORS['text_muted']}; border: none; padding: 4px 10px; border-radius: 4px;")
        btn_del_qp.clicked.connect(self._remove_query_param_row)
        qp_btn_row.addWidget(btn_add_qp)
        qp_btn_row.addWidget(btn_del_qp)
        qp_btn_row.addStretch()
        params_layout.addLayout(qp_btn_row)

        # ── Divider ──
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color: {COLORS['border']};")
        params_layout.addWidget(divider)

        # ── Section: Base64 Query Param ──
        b64_label = QLabel("🔐 Base64-Encoded Query Parameter")
        b64_label.setStyleSheet(f"font-weight: 700; font-size: 9pt; color: {COLORS['accent_purple']}; letter-spacing: 0.5px;")
        params_layout.addWidget(b64_label)

        b64_info = QLabel(
            "Define a JSON object, encode it as Base64, and append it to the URL as a named query parameter."
        )
        b64_info.setWordWrap(True)
        b64_info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 8pt;")
        params_layout.addWidget(b64_info)

        b64_name_row = QHBoxLayout()
        b64_name_row.addWidget(QLabel("Param Name:"), 0)
        self._b64_param_name = QLineEdit()
        self._b64_param_name.setPlaceholderText("e.g. filter  →  ?filter=eyJuYW1lIjoi...")
        self._b64_param_name.textChanged.connect(self.changed.emit)
        b64_name_row.addWidget(self._b64_param_name, 1)
        params_layout.addLayout(b64_name_row)

        b64_json_label = QLabel("JSON Body to Encode:")
        b64_json_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 8pt; font-weight: 600;")
        params_layout.addWidget(b64_json_label)

        self._b64_json_input = QPlainTextEdit()
        self._b64_json_input.setPlaceholderText(
            '{\n  "name": "Container",\n  "page": 0,\n  "size": 10,\n  "sortField": "name",\n  "sortDirection": "ASC"\n}'
        )
        self._b64_json_input.textChanged.connect(self.changed.emit)
        self._b64_highlighter = ApiSyntaxHighlighter(self._b64_json_input.document(), mode="json")
        self._b64_json_input.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {COLORS['bg_darkest']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-family: {FONTS['family_mono']};
                font-size: 12px;
                color: {COLORS['text_primary']};
                padding: 8px;
            }}
        """)
        self._b64_json_input.setMaximumHeight(120)
        params_layout.addWidget(self._b64_json_input)

        b64_action_row = QHBoxLayout()
        btn_encode = QPushButton("🔐 Encode & Preview")
        btn_encode.setStyleSheet(
            f"background: {COLORS['accent_purple']}22; color: {COLORS['accent_purple']};"
            f" font-weight: 700; border: 1px solid {COLORS['accent_purple']}44;"
            f" border-radius: 4px; padding: 6px 14px;"
        )
        btn_encode.clicked.connect(self._encode_b64_param)

        btn_apply_b64 = QPushButton("✅ Apply to URL")
        btn_apply_b64.setStyleSheet(
            f"background: {COLORS['accent_green']}22; color: {COLORS['accent_green']};"
            f" font-weight: 700; border: 1px solid {COLORS['accent_green']}44;"
            f" border-radius: 4px; padding: 6px 14px;"
        )
        btn_apply_b64.clicked.connect(self._apply_b64_to_url)

        b64_action_row.addWidget(btn_encode)
        b64_action_row.addWidget(btn_apply_b64)
        b64_action_row.addStretch()
        params_layout.addLayout(b64_action_row)

        # Preview label
        preview_label = QLabel("Preview:")
        preview_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 8pt; font-weight: 600;")
        params_layout.addWidget(preview_label)

        self._b64_preview = QLineEdit()
        self._b64_preview.setReadOnly(True)
        self._b64_preview.setPlaceholderText("Encoded Base64 value will appear here...")
        self._b64_preview.setStyleSheet(
            f"background: {COLORS['bg_darkest']}; border: 1px solid {COLORS['border']};"
            f" border-radius: 4px; font-family: {FONTS['family_mono']}; font-size: 10px;"
            f" color: {COLORS['accent_green']}; padding: 6px;"
        )
        params_layout.addWidget(self._b64_preview)

        params_layout.addStretch()
        self._request_tabs.addTab(params_widget, "Params")

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


    # ── Base64 Param helpers ──────────────────────────────────────────────────

    def _add_query_param_row(self) -> None:
        row = self._query_params_table.rowCount()
        self._query_params_table.insertRow(row)
        self._query_params_table.setItem(row, 0, QTableWidgetItem(""))
        self._query_params_table.setItem(row, 1, QTableWidgetItem(""))

    def _remove_query_param_row(self) -> None:
        rows = sorted({idx.row() for idx in self._query_params_table.selectedIndexes()}, reverse=True)
        for row in rows:
            self._query_params_table.removeRow(row)
        if not rows:  # nothing selected → remove last
            rc = self._query_params_table.rowCount()
            if rc > 0:
                self._query_params_table.removeRow(rc - 1)
        self.changed.emit()

    def _encode_b64_param(self) -> None:
        """Encode the JSON body as Base64 and show in the preview field."""
        raw = self._b64_json_input.toPlainText().strip()
        if not raw:
            self._b64_preview.setText("")
            self._b64_preview.setPlaceholderText("⚠ Nothing to encode — enter JSON above.")
            return
        try:
            # Validate JSON before encoding
            json.loads(raw)
        except json.JSONDecodeError as exc:
            self._b64_preview.setText("")
            self._b64_preview.setPlaceholderText(f"⚠ Invalid JSON: {exc}")
            return
        encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        self._b64_preview.setText(encoded)

    def _apply_b64_to_url(self) -> None:
        """Append (or replace) the Base64 param in the URL field."""
        self._encode_b64_param()
        encoded = self._b64_preview.text()
        param_name = self._b64_param_name.text().strip()
        if not encoded or not param_name:
            return
        url = self._url_input.text().strip()
        # Remove existing param with same name so we don't duplicate
        import urllib.parse
        parsed = urllib.parse.urlsplit(url)
        qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        qs[param_name] = [encoded]
        new_query = urllib.parse.urlencode({k: v[0] for k, v in qs.items()})
        new_url = urllib.parse.urlunsplit(parsed._replace(query=new_query))
        self._url_input.setText(new_url)
        self.changed.emit()

    # ── Load / Save ──────────────────────────────────────────────────────────

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

        # Query Params
        self._query_params_table.blockSignals(True)
        self._query_params_table.setRowCount(0)
        for k, v in getattr(step, "query_params", {}).items():
            row = self._query_params_table.rowCount()
            self._query_params_table.insertRow(row)
            self._query_params_table.setItem(row, 0, QTableWidgetItem(k))
            self._query_params_table.setItem(row, 1, QTableWidgetItem(v))
        self._query_params_table.blockSignals(False)

        # Base64 Param
        self._b64_param_name.setText(getattr(step, "b64_param_name", ""))
        self._b64_json_input.setPlainText(getattr(step, "b64_param_json", ""))
        self._b64_preview.setText(getattr(step, "b64_param_encoded", ""))

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

        # Query Params
        qp: dict[str, str] = {}
        for row in range(self._query_params_table.rowCount()):
            k_item = self._query_params_table.item(row, 0)
            v_item = self._query_params_table.item(row, 1)
            k = (k_item.text() if k_item else "").strip()
            v = (v_item.text() if v_item else "").strip()
            if k:
                qp[k] = v
        self.step.query_params = qp  # type: ignore[attr-defined]  # dynamic attr

        # Base64 Param
        self.step.b64_param_name = self._b64_param_name.text().strip()  # type: ignore[attr-defined]
        self.step.b64_param_json = self._b64_json_input.toPlainText().strip()  # type: ignore[attr-defined]
        self.step.b64_param_encoded = self._b64_preview.text().strip()  # type: ignore[attr-defined]

