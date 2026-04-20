"""PyShaft Recorder — Element Action Popup.

A rich floating popup that appears at cursor position when an element is
clicked in inspector mode.  Shows locator choices, action buttons, and
assertion buttons so the user can build a test step interactively.
"""

from __future__ import annotations

import time
from functools import partial

from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QRadioButton, QButtonGroup, QLineEdit,
    QInputDialog, QGraphicsDropShadowEffect, QWidget,
    QApplication, QScrollArea, QSizePolicy,
)

from pyshaft.recorder.models import RecordedStep, LocatorSuggestion
from pyshaft.recorder.theme import COLORS, FONTS, ICONS


# ── Actions & Assertions ─────────────────────────────────────────────────

_QUICK_ACTIONS = [
    ("click",        ICONS["click"],      "Click"),
    ("double_click", ICONS["dblclick"],   "Dbl Click"),
    ("right_click",  ICONS["rightclick"], "Right Click"),
    ("type",         ICONS["type"],       "Type…"),
    ("hover",        ICONS["hover"],      "Hover"),
    ("scroll",       ICONS["scroll"],     "Scroll"),
    ("select",       ICONS["select"],     "Select…"),
    ("force_click",  ICONS["force"],      "Force Click"),
    ("upload",       ICONS["upload"],     "Upload…"),
    ("pick_date",    ICONS["date"],       "Pick Date…"),
    ("remove",       ICONS["remove"],     "Remove"),
    ("check",        ICONS["check"],      "Check"),
    ("uncheck",      ICONS["uncheck"],    "Uncheck"),
    ("submit",       ICONS["submit"],     "Submit"),
    ("clear",        "⌫",                "Clear"),
]

_QUICK_ASSERTIONS = [
    ("assert_visible",      ICONS["visible"],  "Visible"),
    ("assert_hidden",       ICONS["hidden"],   "Hidden"),
    ("assert_text",         ICONS["text"],     "Text…"),
    ("assert_enabled",      ICONS["enabled"],  "Enabled"),
    ("assert_disabled",     ICONS["disabled"], "Disabled"),
    ("assert_checked",      ICONS["check"],    "Checked"),
    ("assert_contain_text", "⊃Aa",            "Contains…"),
    ("assert_snapshot",     ICONS["snapshot"], "Snapshot"),
    ("wait_disappear",      "⌛✕",             "Wait Disappear"),
    ("assert_selected_option", ICONS["dropdown"], "▼= Option"),
    ("assert_contain_selected", ICONS["dropdown"], "▼⊃ Option"),
    ("assert_data_type",    ICONS["data_type"], "Data Type…"),
    ("assert_value",        ICONS["get_value"], "Value…"),
]

_QUICK_EXTRACTIONS = [
    ("get_text_as_str",     ICONS["get_text"],  "Text (str)"),
    ("get_text_as_int",     ICONS["cast_int"],   "Text (int)"),
    ("get_text_as_float",   ICONS["cast_float"], "Text (float)"),
    ("get_attribute",       ICONS["extract"],    "Attribute…"),
]


class ElementActionPopup(QFrame):
    """Floating popup for choosing an action/assertion on a selected element.

    Appears at cursor position.  The user picks a locator strategy, optional
    modifier, then clicks an action or assertion button to create a step.
    """

    step_requested = pyqtSignal(object)  # RecordedStep
    dismissed = pyqtSignal()

    # ── construction ──────────────────────────────────────────────────────

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumWidth(390)
        self.setMaximumHeight(520)

        self._element_meta: dict = {}
        self._locator_suggestions: list[LocatorSuggestion] = []
        self._selected_locator_idx: int = 0
        self._selected_modifier: str | None = None
        self._selected_nth: int | None = None

        self._build_ui()
        self._apply_shadow()

    # ── UI construction ───────────────────────────────────────────────────

    def _build_ui(self):
        self.setObjectName("element_popup")
        self.setStyleSheet(self._popup_stylesheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("popup_header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 10, 14, 10)
        hl.setSpacing(8)

        self._tag_label = QLabel("element")
        self._tag_label.setObjectName("popup_tag")
        hl.addWidget(self._tag_label)

        self._loc_preview = QLabel("")
        self._loc_preview.setObjectName("popup_loc_preview")
        self._loc_preview.setStyleSheet(
            f"color:{COLORS['accent_green']};font-family:{FONTS['family_mono']};"
            f"font-size:{FONTS['size_sm']};"
        )
        hl.addWidget(self._loc_preview, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setObjectName("popup_close")
        close_btn.clicked.connect(self._dismiss)
        hl.addWidget(close_btn)

        root.addWidget(header)

        # ── Scrollable body ───────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent;")

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(14, 8, 14, 12)
        body_layout.setSpacing(10)

        # ── Locator choices ───────────────────────────────────────────────
        loc_section = self._section_label("LOCATOR")
        body_layout.addWidget(loc_section)

        self._loc_radio_group = QButtonGroup(self)
        self._loc_container = QVBoxLayout()
        self._loc_container.setSpacing(2)
        self._loc_radios: list[QRadioButton] = []
        body_layout.addLayout(self._loc_container)

        # ── Modifier chips ────────────────────────────────────────────────
        mod_row = QHBoxLayout()
        mod_row.setSpacing(6)
        self._modifier_buttons: dict[str, QPushButton] = {}
        for mod_id, label in [("exact", "Exact"), ("contain", "Contain"), ("starts", "Starts")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("mod_chip")
            btn.clicked.connect(partial(self._on_modifier, mod_id))
            mod_row.addWidget(btn)
            self._modifier_buttons[mod_id] = btn
        # nth
        nth_lbl = QLabel("nth:")
        nth_lbl.setStyleSheet(f"color:{COLORS['text_muted']};font-size:{FONTS['size_sm']};")
        mod_row.addWidget(nth_lbl)
        self._nth_input = QLineEdit()
        self._nth_input.setPlaceholderText("—")
        self._nth_input.setFixedWidth(36)
        self._nth_input.setObjectName("nth_input")
        self._nth_input.textChanged.connect(self._on_nth_changed)
        mod_row.addWidget(self._nth_input)
        mod_row.addStretch()
        body_layout.addLayout(mod_row)

        # ── Divider ──────────────────────────────────────────────────────
        body_layout.addWidget(self._divider())

        # ── Actions ───────────────────────────────────────────────────────
        body_layout.addWidget(self._section_label("ACTIONS"))
        act_grid = QGridLayout()
        act_grid.setSpacing(4)
        for i, (aid, icon, label) in enumerate(_QUICK_ACTIONS):
            btn = QPushButton(f"{icon} {label}")
            btn.setObjectName("act_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(partial(self._on_action, aid))
            act_grid.addWidget(btn, i // 2, i % 2)
        body_layout.addLayout(act_grid)

        # ── Divider ──────────────────────────────────────────────────────
        body_layout.addWidget(self._divider())

        # ── Assertions ────────────────────────────────────────────────────
        body_layout.addWidget(self._section_label("ASSERTIONS"))
        ass_grid = QGridLayout()
        ass_grid.setSpacing(4)
        for i, (aid, icon, label) in enumerate(_QUICK_ASSERTIONS):
            btn = QPushButton(f"{icon} {label}")
            btn.setObjectName("ass_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(partial(self._on_assert, aid))
            ass_grid.addWidget(btn, i // 2, i % 2)
        body_layout.addLayout(ass_grid)

        # \u2500\u2500 Divider \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        body_layout.addWidget(self._divider())

        # \u2500\u2500 Data Extraction \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        body_layout.addWidget(self._section_label("DATA EXTRACTION"))
        ext_grid = QGridLayout()
        ext_grid.setSpacing(4)
        for i, (eid, icon, label) in enumerate(_QUICK_EXTRACTIONS):
            btn = QPushButton(f"{icon} {label}")
            btn.setObjectName("ext_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(partial(self._on_extract, eid))
            ext_grid.addWidget(btn, i // 2, i % 2)
        body_layout.addLayout(ext_grid)

        body_layout.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll)

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color:{COLORS['text_muted']};font-size:{FONTS['size_xs']};"
            f"font-weight:700;letter-spacing:1px;padding:2px 0;"
        )
        return lbl

    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color:{COLORS['border']};")
        line.setFixedHeight(1)
        return line

    def _apply_shadow(self):
        from PyQt6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

    # ── public API ─────────────────────────────────────────────────────────

    def show_for_element(
        self,
        element_meta: dict,
        suggestions: list[LocatorSuggestion],
        global_pos: QPoint | None = None,
    ):
        """Populate and show the popup for a newly inspected element."""
        self._element_meta = element_meta
        self._locator_suggestions = suggestions
        self._selected_locator_idx = 0 if suggestions else -1
        self._selected_modifier = None
        self._selected_nth = None
        self._nth_input.clear()
        for btn in self._modifier_buttons.values():
            btn.setChecked(False)

        # header
        tag = element_meta.get("tag", "?")
        eid = element_meta.get("id", "")
        cls_list = element_meta.get("class", [])
        desc = tag
        if eid:
            desc += f"#{eid}"
        elif cls_list:
            desc += "." + ".".join(cls_list[:2])
        self._tag_label.setText(desc)

        # locator preview
        if suggestions:
            best = suggestions[0]
            self._loc_preview.setText(
                f"{best.locator_type}={best.value[:30]}"
            )
        else:
            self._loc_preview.setText("")

        # rebuild locator radios
        self._rebuild_locator_radios()

        # position & show
        if global_pos is None:
            global_pos = QCursor.pos()

        # Keep popup on-screen
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            x = min(global_pos.x(), sg.right() - self.width() - 8)
            y = min(global_pos.y(), sg.bottom() - self.sizeHint().height() - 8)
            x = max(x, sg.left() + 4)
            y = max(y, sg.top() + 4)
            global_pos = QPoint(x, y)

        self.move(global_pos)
        self.show()
        self.raise_()

    # ── locator radios ────────────────────────────────────────────────────

    def _rebuild_locator_radios(self):
        for r in self._loc_radios:
            self._loc_radio_group.removeButton(r)
            r.deleteLater()
        self._loc_radios.clear()

        stability_colors = {
            "high": COLORS["accent_green"],
            "medium": COLORS["accent_yellow"],
            "low": COLORS["accent_red"],
        }

        for i, sug in enumerate(self._locator_suggestions[:5]):
            color = stability_colors.get(sug.stability, COLORS["text_secondary"])
            mod_part = f".{sug.modifier}" if sug.modifier else ""
            text = f"{sug.locator_type}{mod_part} = \"{sug.value[:40]}\""
            radio = QRadioButton(text)
            radio.setStyleSheet(
                f"QRadioButton{{color:{color};font-family:{FONTS['family_mono']};"
                f"font-size:{FONTS['size_sm']};padding:2px 0;}}"
            )
            radio.setToolTip(f"Stability: {sug.stability} ({sug.score}/100)")
            if i == 0:
                radio.setChecked(True)
            radio.toggled.connect(partial(self._on_locator_selected, i))
            self._loc_radio_group.addButton(radio)
            self._loc_radios.append(radio)
            self._loc_container.addWidget(radio)

    # ── event handlers ────────────────────────────────────────────────────

    def _on_locator_selected(self, idx: int, checked: bool):
        if checked:
            self._selected_locator_idx = idx
            if self._locator_suggestions:
                sug = self._locator_suggestions[idx]
                self._loc_preview.setText(f"{sug.locator_type}={sug.value[:30]}")

    def _on_modifier(self, mod_id: str, *_):
        btn = self._modifier_buttons[mod_id]
        if btn.isChecked():
            self._selected_modifier = mod_id
            for mid, b in self._modifier_buttons.items():
                if mid != mod_id:
                    b.setChecked(False)
        else:
            if self._selected_modifier == mod_id:
                self._selected_modifier = None

    def _on_nth_changed(self, text: str):
        try:
            self._selected_nth = int(text) if text.strip() else None
        except ValueError:
            self._selected_nth = None

    # ── step creation ─────────────────────────────────────────────────────

    def _build_step(self, action: str) -> RecordedStep:
        loc_type = None
        loc_value = ""
        modifier = self._selected_modifier

        if self._locator_suggestions and self._selected_locator_idx >= 0:
            sug = self._locator_suggestions[self._selected_locator_idx]
            loc_type = sug.locator_type
            loc_value = sug.value
            if sug.modifier and not modifier:
                modifier = sug.modifier

        return RecordedStep(
            action=action,
            locator_type=loc_type,
            locator_value=loc_value,
            modifier=modifier,
            index=self._selected_nth,
            timestamp=time.time(),
            url=self._element_meta.get("url", ""),
            element_meta=self._element_meta.copy(),
        )

    def _on_action(self, action_id: str, *_):
        step = self._build_step(action_id)

        if action_id == "type":
            text, ok = QInputDialog.getText(self, "Type Text", "Enter text to type:")
            if not ok:
                return
            step.typed_text = text
        elif action_id == "select":
            text, ok = QInputDialog.getText(self, "Select Option", "Enter option value:")
            if not ok:
                return
            step.typed_text = text

        self._dismiss()
        self.step_requested.emit(step)

    def _on_assert(self, assert_id: str, *_):
        step = self._build_step(assert_id)

        if assert_id in ("assert_text", "assert_contain_text"):
            default = self._element_meta.get("text", "")
            text, ok = QInputDialog.getText(
                self, "Expected Text", "Enter expected text:", text=default
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
                self, "Expected Option", "Enter expected option text:", text=default
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
        elif assert_id == "assert_value":
            default = self._element_meta.get("value", "")
            text, ok = QInputDialog.getText(
                self, "Expected Value", "Enter expected value:", text=default
            )
            if not ok:
                return
            step.assert_expected = text

        self._dismiss()
        self.step_requested.emit(step)

    def _on_extract(self, extract_id: str, *_):
        """Handle data extraction button click — creates an extraction step."""
        step = self._build_step(extract_id)

        # Ask for attribute name if needed
        if extract_id == "get_attribute":
            attr, ok = QInputDialog.getText(self, "Attribute", "Enter attribute name (e.g. href, title):")
            if not ok or not attr:
                return
            step.attribute_name = attr
            default_var = f"attr_{attr}"
        else:
            # Determine cast type from the action
            cast_map = {
                "get_text_as_int": "int",
                "get_text_as_float": "float",
                "get_text_as_str": "str",
            }
            if extract_id in cast_map:
                step.cast_type = cast_map[extract_id]
            default_var = extract_id.replace("get_", "")

        # Ask for variable name
        var_name, ok = QInputDialog.getText(
            self, "Variable Name", "Store result in variable:", text=default_var
        )
        if not ok:
            return
        step.extract_variable = var_name or default_var

        self._dismiss()
        self.step_requested.emit(step)

    def _dismiss(self):
        self.hide()
        self.dismissed.emit()

    # ── stylesheet ────────────────────────────────────────────────────────

    @staticmethod
    def _popup_stylesheet() -> str:
        c = COLORS
        f = FONTS
        return f"""
        QFrame#element_popup {{
            background-color: {c['bg_medium']};
            border: 1px solid {c['accent_purple']};
            border-radius: 12px;
        }}

        /* ── header ── */
        QFrame#popup_header {{
            background-color: {c['bg_dark']};
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            border-bottom: 1px solid {c['border']};
        }}
        QLabel#popup_tag {{
            color: {c['accent_blue']};
            font-family: {f['family_mono']};
            font-size: {f['size_md']};
            font-weight: 700;
        }}
        QPushButton#popup_close {{
            background: transparent;
            color: {c['text_muted']};
            border: none;
            font-size: 13px;
            border-radius: 11px;
        }}
        QPushButton#popup_close:hover {{
            background-color: {c['accent_red']};
            color: #FFFFFF;
        }}

        /* ── modifier chips ── */
        QPushButton#mod_chip {{
            background-color: {c['bg_card']};
            border: 1px solid {c['border']};
            border-radius: 4px;
            padding: 3px 10px;
            font-size: {f['size_sm']};
            color: {c['text_secondary']};
        }}
        QPushButton#mod_chip:checked {{
            background-color: {c['accent_purple_dim']};
            border-color: {c['accent_purple']};
            color: {c['text_primary']};
        }}
        QPushButton#mod_chip:hover {{
            border-color: {c['border_light']};
        }}

        /* ── nth input ── */
        QLineEdit#nth_input {{
            background-color: {c['bg_card']};
            border: 1px solid {c['border']};
            border-radius: 4px;
            padding: 3px 6px;
            font-size: {f['size_sm']};
            color: {c['text_primary']};
            font-family: {f['family_mono']};
        }}
        QLineEdit#nth_input:focus {{
            border-color: {c['accent_purple']};
        }}

        /* ── action buttons ── */
        QPushButton#act_btn {{
            background-color: {c['bg_card']};
            border: 1px solid {c['border']};
            border-radius: 5px;
            padding: 5px 4px;
            font-size: {f['size_sm']};
            color: {c['text_primary']};
        }}
        QPushButton#act_btn:hover {{
            background-color: {c['accent_purple_dim']};
            border-color: {c['accent_purple']};
        }}

        /* ── assertion buttons ── */
        QPushButton#ass_btn {{
            background-color: {c['bg_card']};
            border: 1px solid {c['border']};
            border-radius: 5px;
            padding: 5px 4px;
            font-size: {f['size_sm']};
            color: {c['text_primary']};
        }}
        QPushButton#ass_btn:hover {{
            background-color: {c['accent_green_dim']};
            border-color: {c['accent_green']};
        }}

        /* ── extraction buttons ── */
        QPushButton#ext_btn {{
            background-color: {c['bg_card']};
            border: 1px solid {c['border']};
            border-radius: 5px;
            padding: 5px 4px;
            font-size: {f['size_sm']};
            color: {c['text_primary']};
        }}
        QPushButton#ext_btn:hover {{
            background-color: {c['accent_orange']}22;
            border-color: {c['accent_orange']};
        }}
        """
