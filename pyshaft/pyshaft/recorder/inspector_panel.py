"""PyShaft Recorder — Inspector Panel (right sidebar).

Shows element information, action/assert buttons, locator choices, and search.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QRadioButton, QButtonGroup,
    QLineEdit, QGroupBox, QCheckBox, QInputDialog, QComboBox, QFileDialog, QMessageBox,
)

from pyshaft.recorder.models import RecordedStep, LocatorSuggestion
from pyshaft.recorder.theme import COLORS, FONTS, ICONS

import time


# All available actions with their icons and categories
_ACTIONS = [
    ("click", ICONS["click"], "Click"),
    ("double_click", ICONS["dblclick"], "Dbl Click"),
    ("right_click", ICONS["rightclick"], "Right Click"),
    ("type", ICONS["type"], "Type..."),
    ("hover", ICONS["hover"], "Hover"),
    ("scroll", ICONS["scroll"], "Scroll To"),
    ("select", ICONS["select"], "Select..."),
    ("check", ICONS["check"], "Check"),
    ("uncheck", ICONS["uncheck"], "Uncheck"),
    ("submit", ICONS["submit"], "Submit"),
    ("drag", ICONS["drag"], "Drag"),
    ("clear", "⌫", "Clear"),
]

_ASSERTIONS = [
    ("assert_visible", ICONS["visible"], "Visible"),
    ("assert_hidden", ICONS["hidden"], "Hidden"),
    ("assert_text", ICONS["text"], "Text..."),
    ("assert_enabled", ICONS["enabled"], "Enabled"),
    ("assert_disabled", ICONS["disabled"], "Disabled"),
    ("assert_checked", ICONS["check"], "Checked"),
    ("assert_snapshot", ICONS["snapshot"], "Snapshot"),
    ("assert_aria_snapshot", "📐", "Aria Snap"),
    ("assert_title", ICONS["title"], "Title..."),
    ("assert_url", ICONS["url"], "URL..."),
    ("assert_contain_text", "⊃Aa", "Contains Text..."),
    ("assert_contain_title", "⊃📄", "Contains Title..."),
    ("assert_contain_url", "⊃🔗", "Contains URL..."),
    ("assert_selected_option", ICONS["dropdown"], "▼= Option"),
    ("assert_contain_selected", ICONS["dropdown"], "▼⊃ Option"),
    ("assert_data_type", ICONS["data_type"], "Data Type..."),
    ("assert_value", ICONS["get_value"], "Value..."),
]

_EXTRACTIONS = [
    ("get_text", ICONS["get_text"], "Get Text"),
    ("get_value", ICONS["get_value"], "Get Value"),
    ("get_text_as_int", ICONS["cast_int"], "Text → Int"),
    ("get_text_as_float", ICONS["cast_float"], "Text → Float"),
    ("get_text_as_str", ICONS["get_text"], "Text → Str"),
    ("get_selected_option", ICONS["dropdown"], "Get Selected"),
]

# Searchable commands (all actions + assertions + extractions combined)
_ALL_COMMANDS = _ACTIONS + _ASSERTIONS + _EXTRACTIONS


class InspectorPanel(QWidget):
    """Right sidebar showing element info, actions, assertions, and locator choices."""

    step_requested = pyqtSignal(object)  # RecordedStep
    snapshot_capture_requested = pyqtSignal(str, object)  # (name, element_meta)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._element_meta: dict = {}
        self._locator_suggestions: list[LocatorSuggestion] = []
        self._selected_locator_index: int = 0
        self._selected_modifier: str | None = None
        self._selected_index: int | None = None
        self._setup_ui()

    def _create_aria_tree_section(self) -> QGroupBox:
        """Create the Aria Tree visualization section."""
        group = QGroupBox("📐 ARIA TREE")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(6)
        
        self._aria_label = QLabel("—")
        self._aria_label.setStyleSheet(f"""
            color: {COLORS['accent_green']};
            font-family: {FONTS['family_mono']};
            font-size: 11px;
            background-color: {COLORS['bg_darkest']};
            padding: 8px;
            border-radius: 4px;
        """)
        self._aria_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._aria_label.setWordWrap(True)
        layout.addWidget(self._aria_label)
        
        return group

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("panel_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        title = QLabel("🔍 Inspector")
        title.setObjectName("title")
        title.setStyleSheet(f"font-size: {FONTS['size_md']}; font-weight: 700;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        main_layout.addWidget(header)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background-color: {COLORS['bg_darkest']};")

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(12, 8, 12, 8)
        self._content_layout.setSpacing(12)

        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔎  Search actions & assertions...")
        self._search.textChanged.connect(self._on_search_changed)
        self._content_layout.addWidget(self._search)

        # Element Info Section
        self._info_group = self._create_element_info_section()
        self._content_layout.addWidget(self._info_group)
        
        # Aria Tree Section
        self._aria_group = self._create_aria_tree_section()
        self._content_layout.addWidget(self._aria_group)

        # Actions Section
        self._actions_group = self._create_actions_section()
        self._content_layout.addWidget(self._actions_group)

        # Assertions Section
        self._asserts_group = self._create_assertions_section()
        self._content_layout.addWidget(self._asserts_group)

        # Data Extraction Section
        self._extract_group = self._create_extraction_section()
        self._content_layout.addWidget(self._extract_group)

        # Locator Section
        self._locator_group = self._create_locator_section()
        self._content_layout.addWidget(self._locator_group)

        # Modifier toggles
        self._modifier_group = self._create_modifier_section()
        self._content_layout.addWidget(self._modifier_group)

        self._content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # Initial state
        self._set_no_element_state()

    # -------------------------------------------------------------------------
    # Section Builders
    # -------------------------------------------------------------------------

    def _create_element_info_section(self) -> QGroupBox:
        """Create the Element Information section."""
        group = QGroupBox("ELEMENT INFO")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(6)

        self._info_labels = {}
        fields = [
            ("tag", "Tag"), ("id", "ID"), ("class", "Class"),
            ("role", "Role"), ("data-testid", "Test ID"),
            ("text", "Text"), ("value", "Value"), ("href", "Href"),
        ]

        for key, label_text in fields:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(60)
            lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: bold; text-transform: uppercase;")
            row.addWidget(lbl)

            val = QLabel("—")
            val.setStyleSheet(f"""
                color: {COLORS['text_primary']};
                font-family: {FONTS['family_mono']};
                font-size: 11px;
                background-color: {COLORS['bg_darkest']};
                padding: 2px 6px;
                border-radius: 3px;
            """)
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(val, 1)

            self._info_labels[key] = val
            layout.addLayout(row)

        return group

    def _create_actions_section(self) -> QGroupBox:
        """Create the Actions button grid."""
        group = QGroupBox(f"{ICONS['click']}  ACTIONS")
        grid = QGridLayout(group)
        grid.setContentsMargins(8, 20, 8, 8)
        grid.setSpacing(6)

        self._action_buttons = {}
        for i, (action_id, icon, label) in enumerate(_ACTIONS):
            btn = QPushButton(f"{icon} {label}")
            btn.setProperty("class", "action_btn")
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"w.{action_id}()")
            btn.clicked.connect(lambda checked, a=action_id: self._on_action_clicked(a))
            grid.addWidget(btn, i // 2, i % 2) # 2 columns for better readability
            self._action_buttons[action_id] = btn

        return group

    def _create_assertions_section(self) -> QGroupBox:
        """Create the Assertions button grid."""
        group = QGroupBox(f"{ICONS['assert']}  ASSERTIONS")
        grid = QGridLayout(group)
        grid.setContentsMargins(8, 20, 8, 8)
        grid.setSpacing(6)

        self._assert_buttons = {}
        for i, (assert_id, icon, label) in enumerate(_ASSERTIONS):
            btn = QPushButton(f"{icon} {label}")
            btn.setProperty("class", "assert_btn")
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"w.{assert_id}()")
            btn.clicked.connect(lambda checked, a=assert_id: self._on_assert_clicked(a))
            grid.addWidget(btn, i // 2, i % 2) # 2 columns
            self._assert_buttons[assert_id] = btn

        return group


    def _create_extraction_section(self) -> QGroupBox:
        """Create the Data Extraction button grid."""
        group = QGroupBox(f"{ICONS['extract']}  EXTRACTION")
        grid = QGridLayout(group)
        grid.setContentsMargins(8, 20, 8, 8)
        grid.setSpacing(6)

        self._extract_buttons = {}
        for i, (extract_id, icon, label) in enumerate(_EXTRACTIONS):
            btn = QPushButton(f"{icon} {label}")
            btn.setToolTip(f"w.{extract_id}()")
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['bg_card']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent_orange']}22;
                    border-color: {COLORS['accent_orange']};
                }}
            """)
            btn.clicked.connect(lambda checked, a=extract_id: self._on_extract_clicked(a))
            grid.addWidget(btn, i // 2, i % 2)
            self._extract_buttons[extract_id] = btn

        return group

    def _create_locator_section(self) -> QGroupBox:
        """Create the Locator selection section with radio buttons."""
        group = QGroupBox(f"{ICONS['nav']}  LOCATOR STRATEGY")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 20, 8, 8)
        layout.setSpacing(4)

        self._locator_radio_group = QButtonGroup(self)
        self._locator_radios: list[QRadioButton] = []
        self._locator_container = layout

        # Placeholder label shown when no element selected
        self._no_locator_label = QLabel("Select an element to see options")
        self._no_locator_label.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: 11px;
            padding: 8px;
        """)
        layout.addWidget(self._no_locator_label)

        return group


    def _create_modifier_section(self) -> QGroupBox:
        """Create the modifier toggles (Exact/Contain/Starts/nth)."""
        group = QGroupBox("MODIFIERS")
        layout = QHBoxLayout(group)
        layout.setSpacing(6)

        self._modifier_buttons = {}
        for mod_id, label in [("exact", "Exact"), ("contain", "Contain"), ("starts", "Starts")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['bg_card']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: {FONTS['size_sm']};
                    color: {COLORS['text_secondary']};
                }}
                QPushButton:checked {{
                    background-color: {COLORS['accent_purple_dim']};
                    border-color: {COLORS['accent_purple']};
                    color: {COLORS['text_primary']};
                }}
                QPushButton:hover {{
                    border-color: {COLORS['border_light']};
                }}
            """)
            btn.clicked.connect(lambda checked, m=mod_id: self._on_modifier_toggled(m, checked))
            layout.addWidget(btn)
            self._modifier_buttons[mod_id] = btn

        # nth input
        nth_label = QLabel("nth:")
        nth_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: {FONTS['size_sm']};")
        layout.addWidget(nth_label)

        self._nth_input = QLineEdit()
        self._nth_input.setPlaceholderText("1")
        self._nth_input.setFixedWidth(40)
        self._nth_input.setStyleSheet(f"font-size: {FONTS['size_sm']}; padding: 4px;")
        self._nth_input.textChanged.connect(self._on_nth_changed)
        layout.addWidget(self._nth_input)

        return group

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def set_element(self, element_meta: dict, locator_suggestions: list[LocatorSuggestion]):
        """Update the inspector with data from a newly selected element."""
        self._element_meta = element_meta
        self._locator_suggestions = locator_suggestions
        self._selected_locator_index = 0 if locator_suggestions else -1

        # Update element info labels
        for key, label in self._info_labels.items():
            value = element_meta.get(key, "")
            if isinstance(value, list):
                value = " ".join(value)
            label.setText(str(value) if value else "—")
            if value:
                label.setStyleSheet(f"""
                    color: {COLORS['text_primary']};
                    font-family: {FONTS['family_mono']};
                    font-size: 11px;
                    background-color: {COLORS['bg_darkest']};
                    padding: 2px 6px;
                    border-radius: 3px;
                """)
            else:
                label.setStyleSheet(f"""
                    color: {COLORS['text_muted']};
                    font-size: 11px;
                """)

        # Update Aria Tree
        from pyshaft.web import aria
        tree = element_meta.get("aria_tree") or {}
        yaml_text = aria.tree_to_yaml(tree) if tree else "—"
        self._aria_label.setText(yaml_text)

        # Update locator radio buttons
        self._refresh_locators()

        # Enable action/assert/extract buttons
        for btn in self._action_buttons.values():
            btn.setEnabled(True)
        for btn in self._assert_buttons.values():
            btn.setEnabled(True)
        for btn in self._extract_buttons.values():
            btn.setEnabled(True)

    def _set_no_element_state(self):
        """Set the panel to its default "no element selected" state."""
        for label in self._info_labels.values():
            label.setText("—")
            label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        
        self._aria_label.setText("—")

        # Disable action/assert/extract buttons until element selected
        for btn in self._action_buttons.values():
            btn.setEnabled(False)
        for btn in self._assert_buttons.values():
            btn.setEnabled(False)
        for btn in self._extract_buttons.values():
            btn.setEnabled(False)

    def _refresh_locators(self):
        """Rebuild the locator radio buttons based on current suggestions."""
        # Clear existing radios
        for radio in self._locator_radios:
            self._locator_radio_group.removeButton(radio)
            radio.deleteLater()
        self._locator_radios.clear()
        self._no_locator_label.setVisible(not self._locator_suggestions)

        stability_colors = {
            "high": COLORS["accent_green"],
            "medium": COLORS["accent_yellow"],
            "low": COLORS["accent_red"],
        }

        for i, suggestion in enumerate(self._locator_suggestions):
            color = stability_colors.get(suggestion.stability, COLORS["text_secondary"])
            mod_text = f".{suggestion.modifier}" if suggestion.modifier else ""
            label = f"● {suggestion.locator_type}{mod_text} = \"{suggestion.value}\""

            radio = QRadioButton(label)
            radio.setStyleSheet(f"""
                QRadioButton {{
                    color: {color};
                    font-family: {FONTS['family_mono']};
                    font-size: {FONTS['size_sm']};
                    padding: 4px 0;
                }}
            """)
            radio.setToolTip(f"Stability: {suggestion.stability} ({suggestion.score}/100)")

            if i == 0:
                radio.setChecked(True)

            radio.toggled.connect(lambda checked, idx=i: self._on_locator_selected(idx, checked))
            self._locator_radio_group.addButton(radio)
            self._locator_radios.append(radio)
            self._locator_container.addWidget(radio)

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def _on_action_clicked(self, action_id: str):
        """Handle action button click — create a RecordedStep."""
        step = self._build_step(action_id)

        # Actions that need extra input
        if action_id == "type":
            text, ok = QInputDialog.getText(self, "Type Text", "Enter text to type:")
            if not ok:
                return
            step.typed_text = text
        elif action_id == "select":
            text, ok = QInputDialog.getText(
                self, "Select Option", "Enter option text, value, or index:"
            )
            if not ok:
                return
            step.typed_text = text

        self.step_requested.emit(step)

    def _on_assert_clicked(self, assert_id: str):
        """Handle assertion button click — create an assertion step."""
        step = self._build_step(assert_id)

        # Assertions that need expected values
        if assert_id in ("assert_text", "assert_contain_text"):
            # Pre-fill with element's text content
            default_text = self._element_meta.get("text", "")
            text, ok = QInputDialog.getText(
                self, "Expected Text", "Enter expected text:",
                text=default_text
            )
            if not ok:
                return
            step.assert_expected = text
        elif assert_id in ("assert_title", "assert_contain_title"):
            text, ok = QInputDialog.getText(self, "Expected Title", "Enter expected title:")
            if not ok:
                return
            step.assert_expected = text
        elif assert_id in ("assert_url", "assert_contain_url"):
            text, ok = QInputDialog.getText(self, "Expected URL", "Enter expected URL:")
            if not ok:
                return
            step.assert_expected = text
        elif assert_id in ("assert_selected_option", "assert_contain_selected"):
            default = self._element_meta.get("selected_text", "")
            text, ok = QInputDialog.getText(
                self, "Expected Option", "Enter expected option text, value, or index:", text=default
            )
            if not ok:
                return
            step.assert_expected = text
        elif assert_id == "assert_data_type":
            types = ["int", "float", "string", "bool", "email", "url", "date",
                     "phone", "uuid", "empty", "not_empty", "number"]
            dtype, ok = QInputDialog.getItem(
                self, "Data Type", "Select expected data type:", types, 0, False
            )
            if not ok:
                return
            step.assert_data_type_name = dtype
        elif assert_id == "assert_snapshot":
            from pathlib import Path
            base_dir = Path("saved_snapshots")
            existing = []
            if base_dir.exists():
                existing = [f.stem for f in base_dir.glob("*.png")]
            
            msg = "Select a baseline or 'Browse...' to pick a file:"
            choices = ["Browse..."] + sorted(existing)
            
            choice, ok = QInputDialog.getItem(self, "Assert Snapshot", msg, choices, 0, True)
            if not ok: return
            
            if choice == "Browse...":
                path, _ = QFileDialog.getOpenFileName(self, "Select baseline file", str(base_dir), "Images (*.png)")
                if not path: return
                step.assert_expected = Path(path).stem
            else:
                step.assert_expected = choice
                # Trigger capture
                self.snapshot_capture_requested.emit(step.assert_expected, self._element_meta)
        elif assert_id == "assert_aria_snapshot":
            from pyshaft.web import aria
            try:
                tree = self._element_meta.get("aria_tree") or {}
                yaml_text = aria.tree_to_yaml(tree)
                text, ok = QInputDialog.getMultiLineText(
                    self, "Aria Snapshot", "Verify semantic structure (YAML):", text=yaml_text
                )
                if not ok: return
                step.assert_expected = text
            except Exception as e:
                QMessageBox.warning(self, "Aria Error", f"Failed to capture Aria Tree: {e}")
                return
        elif assert_id == "assert_value":
            default = self._element_meta.get("value", "")
            text, ok = QInputDialog.getText(
                self, "Expected Value", "Enter expected value:", text=default
            )
            if not ok:
                return
            step.assert_expected = text

        self.step_requested.emit(step)

    def _on_extract_clicked(self, extract_id: str):
        """Handle data extraction button click — create an extraction step."""
        step = self._build_step(extract_id)

        # Determine cast type from the action
        cast_map = {
            "get_text_as_int": "int",
            "get_text_as_float": "float",
            "get_text_as_str": "str",
        }
        if extract_id in cast_map:
            step.cast_type = cast_map[extract_id]

        # Ask for variable name
        default_var = extract_id.replace("get_", "")
        var_name, ok = QInputDialog.getText(
            self, "Variable Name", "Store result in variable:", text=default_var
        )
        if not ok:
            return
        step.extract_variable = var_name or default_var

        self.step_requested.emit(step)

    def _build_step(self, action: str) -> RecordedStep:
        """Build a RecordedStep from the current inspector state."""
        # Get selected locator
        loc_type = None
        loc_value = ""
        modifier = self._selected_modifier

        if self._locator_suggestions and self._selected_locator_index >= 0:
            suggestion = self._locator_suggestions[self._selected_locator_index]
            loc_type = suggestion.locator_type
            loc_value = suggestion.value
            if suggestion.modifier and not modifier:
                modifier = suggestion.modifier

        # Get nth index
        nth = self._selected_index

        return RecordedStep(
            action=action,
            locator_type=loc_type,
            locator_value=loc_value,
            modifier=modifier,
            index=nth,
            timestamp=time.time(),
            url=self._element_meta.get("url", ""),
            element_meta=self._element_meta.copy(),
        )

    def _on_locator_selected(self, index: int, checked: bool):
        if checked:
            self._selected_locator_index = index

    def _on_modifier_toggled(self, modifier: str, checked: bool):
        """Handle modifier button toggle — ensure only one is active."""
        if checked:
            self._selected_modifier = modifier
            # Uncheck others
            for mid, btn in self._modifier_buttons.items():
                if mid != modifier:
                    btn.setChecked(False)
        else:
            if self._selected_modifier == modifier:
                self._selected_modifier = None

    def _on_nth_changed(self, text: str):
        try:
            self._selected_index = int(text) if text.strip() else None
        except ValueError:
            self._selected_index = None

    def _on_search_changed(self, text: str):
        """Filter action/assertion/extraction buttons based on search text."""
        search = text.lower().strip()

        for action_id, btn in self._action_buttons.items():
            visible = not search or search in action_id.lower() or search in btn.text().lower()
            btn.setVisible(visible)

        for assert_id, btn in self._assert_buttons.items():
            visible = not search or search in assert_id.lower() or search in btn.text().lower()
            btn.setVisible(visible)

        for extract_id, btn in self._extract_buttons.items():
            visible = not search or search in extract_id.lower() or search in btn.text().lower()
            btn.setVisible(visible)

        # Show/hide sections based on whether any buttons visible
        any_actions = any(btn.isVisible() for btn in self._action_buttons.values())
        any_asserts = any(btn.isVisible() for btn in self._assert_buttons.values())
        any_extracts = any(btn.isVisible() for btn in self._extract_buttons.values())
        self._actions_group.setVisible(any_actions or not search)
        self._asserts_group.setVisible(any_asserts or not search)
        self._extract_group.setVisible(any_extracts or not search)
