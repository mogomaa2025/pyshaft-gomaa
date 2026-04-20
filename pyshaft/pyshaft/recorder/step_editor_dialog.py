"""PyShaft Recorder — Step Editor Dialog.

A dialog for editing step details (action, locator, filters, etc.).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QFrame, QGroupBox,
    QRadioButton, QButtonGroup, QSpinBox, QCheckBox,
    QPlainTextEdit, QWidget, QScrollArea,
)

from pyshaft.recorder.models import RecordedStep
from pyshaft.recorder.theme import COLORS, FONTS


# All actions available in the dropdown
_ALL_ACTIONS = [
    "click", "double_click", "right_click", "type", "hover", "scroll",
    "select", "select_dynamic", "check", "uncheck", "submit", "drag", "clear",
    "pick_date", "upload_file", "remove_element",
    "wait_until_disappears", "switch_to_iframe", "switch_to_default",
    "accept_alert", "dismiss_alert", "get_alert_text",
    "assert_visible", "assert_hidden", "assert_text", "assert_enabled",
    "assert_disabled", "assert_checked", "assert_title", "assert_url",
    "assert_contain_text", "assert_contain_title", "assert_contain_url",
    "assert_snapshot",
    "open_url", "go_back", "go_forward", "refresh",
]

# Locator types
_LOCATOR_TYPES = [
    "", "role", "text", "label", "placeholder", "testid",
    "id", "class", "css", "xpath", "tag", "attr", "any",
]


class StepEditorDialog(QDialog):
    """Dialog to edit a recorded step's details."""

    def __init__(self, step: RecordedStep, parent=None):
        super().__init__(parent)
        self.step = step
        self._result_step: RecordedStep | None = None
        self.setWindowTitle("Edit Step")
        self.setMinimumWidth(550)
        self.setMinimumHeight(650)
        self.resize(600, 700)
        self._setup_ui()
        self._populate_from_step()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area for form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")
        
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("✎  Edit Step")
        title.setStyleSheet(f"""
            font-size: {FONTS['size_xl']};
            font-weight: 700;
            color: {COLORS['text_primary']};
            padding-bottom: 8px;
        """)
        layout.addWidget(title)

        def create_group(title_text):
            container = QFrame()
            container.setObjectName("group_container")
            container.setStyleSheet(f"""
                QFrame#group_container {{
                    background-color: {COLORS['bg_dark']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                }}
            """)
            clayout = QVBoxLayout(container)
            clayout.setContentsMargins(12, 16, 12, 16)
            clayout.setSpacing(8)
            
            label = QLabel(title_text)
            label.setStyleSheet(f"""
                color: {COLORS['text_secondary']};
                font-size: {FONTS['size_xs']};
                font-weight: bold;
            """)
            clayout.addWidget(label)
            return container, clayout

        # --- Action Section ---
        action_group, action_main = create_group("ACTION")
        action_layout = QFormLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)
        action_main.addLayout(action_layout)

        self._action_combo = QComboBox()
        self._action_combo.addItems(_ALL_ACTIONS)
        self._action_combo.currentTextChanged.connect(self._on_action_changed)
        action_layout.addRow("Action:", self._action_combo)

        # Text input (for type, select)
        self._text_input = QLineEdit()
        self._text_input.setPlaceholderText("Text to type or option to select")
        action_layout.addRow("Text:", self._text_input)

        # Expected value (for assertions)
        self._expected_input = QLineEdit()
        self._expected_input.setPlaceholderText("Expected value for assertion")
        action_layout.addRow("Expected:", self._expected_input)

        layout.addWidget(action_group)

        # --- Locator Section ---
        locator_group, locator_main = create_group("LOCATOR")
        locator_layout = QFormLayout()
        locator_layout.setContentsMargins(0, 0, 0, 0)
        locator_layout.setSpacing(8)
        locator_main.addLayout(locator_layout)

        self._loc_type_combo = QComboBox()
        self._loc_type_combo.addItems(_LOCATOR_TYPES)
        locator_layout.addRow("Type:", self._loc_type_combo)

        self._loc_value_input = QLineEdit()
        self._loc_value_input.setPlaceholderText("Locator value")
        locator_layout.addRow("Value:", self._loc_value_input)

        # Modifier
        mod_layout = QHBoxLayout()
        self._mod_group = QButtonGroup(self)
        self._mod_none = QRadioButton("None")
        self._mod_exact = QRadioButton("Exact")
        self._mod_contain = QRadioButton("Contain")
        self._mod_starts = QRadioButton("Starts")
        self._mod_group.addButton(self._mod_none)
        self._mod_group.addButton(self._mod_exact)
        self._mod_group.addButton(self._mod_contain)
        self._mod_group.addButton(self._mod_starts)
        mod_layout.addWidget(self._mod_none)
        mod_layout.addWidget(self._mod_exact)
        mod_layout.addWidget(self._mod_contain)
        mod_layout.addWidget(self._mod_starts)
        locator_layout.addRow("Modifier:", mod_layout)

        # Index
        self._index_spin = QSpinBox()
        self._index_spin.setRange(-100, 100)
        self._index_spin.setSpecialValueText("None")
        self._index_spin.setValue(0)
        locator_layout.addRow("nth():", self._index_spin)

        layout.addWidget(locator_group)

        # --- Filters Section ---
        filter_group, filter_layout = create_group("FILTERS")

        self._filter_input = QPlainTextEdit()
        self._filter_input.setPlaceholderText('key=value pairs, one per line\nExample:\nclass_=primary\ntype=submit')
        self._filter_input.setMaximumHeight(80)
        filter_layout.addWidget(self._filter_input)

        layout.addWidget(filter_group)

        # --- Inside Section ---
        inside_group, inside_main = create_group("INSIDE (Parent Container)")
        inside_layout = QFormLayout()
        inside_layout.setContentsMargins(0, 0, 0, 0)
        inside_main.addLayout(inside_layout)

        self._inside_type_combo = QComboBox()
        self._inside_type_combo.addItems(_LOCATOR_TYPES)
        inside_layout.addRow("Type:", self._inside_type_combo)

        self._inside_value_input = QLineEdit()
        self._inside_value_input.setPlaceholderText("Parent container value (optional)")
        inside_layout.addRow("Value:", self._inside_value_input)

        layout.addWidget(inside_group)

        # --- Code Preview ---
        preview_group, preview_layout = create_group("CODE PREVIEW")

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setMaximumHeight(60)
        self._preview.setStyleSheet(f"""
            font-family: {FONTS['family_mono']};
            font-size: {FONTS['size_sm']};
            color: {COLORS['accent_green']};
            background-color: {COLORS['bg_darkest']};
        """)
        preview_layout.addWidget(self._preview)

        layout.addWidget(preview_group)
        layout.addStretch()  # Prevent components from expanding vertically

        main_layout.addWidget(scroll_area)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 0, 20, 20)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        main_layout.addLayout(btn_layout)

        # Connect changes to preview update
        for widget in [self._action_combo, self._loc_type_combo, self._inside_type_combo]:
            widget.currentTextChanged.connect(self._update_preview)
        for widget in [self._text_input, self._expected_input, self._loc_value_input,
                       self._inside_value_input]:
            widget.textChanged.connect(self._update_preview)
        self._index_spin.valueChanged.connect(self._update_preview)
        self._mod_group.buttonToggled.connect(self._update_preview)
        self._filter_input.textChanged.connect(self._update_preview)

    def _populate_from_step(self):
        """Fill the form from the current step."""
        idx = self._action_combo.findText(self.step.action)
        if idx >= 0:
            self._action_combo.setCurrentIndex(idx)

        self._text_input.setText(self.step.typed_text or "")
        self._expected_input.setText(self.step.assert_expected or "")

        idx = self._loc_type_combo.findText(self.step.locator_type or "")
        if idx >= 0:
            self._loc_type_combo.setCurrentIndex(idx)
        self._loc_value_input.setText(self.step.locator_value)

        # Modifier
        if self.step.modifier == "exact":
            self._mod_exact.setChecked(True)
        elif self.step.modifier == "contain":
            self._mod_contain.setChecked(True)
        elif self.step.modifier == "starts":
            self._mod_starts.setChecked(True)
        else:
            self._mod_none.setChecked(True)

        # Index
        if self.step.index is not None:
            self._index_spin.setValue(self.step.index)

        # Filters
        if self.step.filters:
            filter_text = "\n".join(f"{k}={v}" for k, v in self.step.filters.items())
            self._filter_input.setPlainText(filter_text)

        # Inside
        if self.step.inside:
            inside_type, inside_value = self.step.inside
            idx = self._inside_type_combo.findText(inside_type)
            if idx >= 0:
                self._inside_type_combo.setCurrentIndex(idx)
            self._inside_value_input.setText(inside_value)

        self._on_action_changed(self.step.action)
        self._update_preview()

    def _on_action_changed(self, action: str):
        """Show/hide fields based on action type."""
        is_type = action in ("type", "select")
        is_assert_with_expected = action in (
            "assert_text", "assert_title", "assert_url",
            "assert_contain_text", "assert_contain_title", "assert_contain_url",
        )
        is_nav = action in ("open_url", "go_back", "go_forward", "refresh")

        self._text_input.setVisible(is_type)
        self._expected_input.setVisible(is_assert_with_expected)

    def _update_preview(self):
        """Update the code preview based on current form state."""
        step = self._build_step_from_form()
        from pyshaft.recorder.code_generator import _step_to_code
        try:
            code = "w." + _step_to_code(step).lstrip("w.")
            self._preview.setPlainText(code)
        except Exception:
            self._preview.setPlainText("# (preview error)")

    def _build_step_from_form(self) -> RecordedStep:
        """Build a RecordedStep from the current form values."""
        # Parse filters
        filters = {}
        for line in self._filter_input.toPlainText().strip().split("\n"):
            if "=" in line:
                k, v = line.split("=", 1)
                filters[k.strip()] = v.strip()

        # Parse inside
        inside = None
        inside_type = self._inside_type_combo.currentText()
        inside_value = self._inside_value_input.text().strip()
        if inside_type and inside_value:
            inside = (inside_type, inside_value)

        # Modifier
        modifier = None
        if self._mod_exact.isChecked():
            modifier = "exact"
        elif self._mod_contain.isChecked():
            modifier = "contain"
        elif self._mod_starts.isChecked():
            modifier = "starts"

        # Index
        index = self._index_spin.value() if self._index_spin.value() != 0 else None

        return RecordedStep(
            id=self.step.id,
            action=self._action_combo.currentText(),
            locator_type=self._loc_type_combo.currentText() or None,
            locator_value=self._loc_value_input.text(),
            modifier=modifier,
            typed_text=self._text_input.text() or None,
            filters=filters,
            inside=inside,
            index=index,
            assert_expected=self._expected_input.text() or None,
            timestamp=self.step.timestamp,
            url=self.step.url,
            element_meta=self.step.element_meta,
        )

    def _on_save(self):
        self._result_step = self._build_step_from_form()
        self.accept()

    def get_result(self) -> RecordedStep | None:
        """Get the edited step (only valid after accept())."""
        return self._result_step
