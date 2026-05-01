"""PyShaft Recorder — Dark theme and color palette.

Modern dark UI with purple/green accents inspired by premium dev tools.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Color Palette
# ---------------------------------------------------------------------------

COLORS = {
    # Base
    "bg_darkest": "#0D1117",
    "bg_dark": "#161B22",
    "bg_medium": "#1C2333",
    "bg_light": "#21283B",
    "bg_card": "#242D3D",
    "bg_hover": "#2D3750",
    "bg_selected": "#343F56",

    # Borders
    "border": "#30363D",
    "border_light": "#3D4654",
    "border_focus": "#6C63FF",

    # Text
    "text_primary": "#E6EDF3",
    "text_secondary": "#8B949E",
    "text_muted": "#6E7681",
    "text_link": "#79C0FF",

    # Accent colors
    "accent_purple": "#6C63FF",
    "accent_purple_hover": "#8078FF",
    "accent_purple_dim": "#4A44B2",
    "accent_green": "#00D9A3",
    "accent_green_hover": "#33E5B8",
    "accent_green_dim": "#00A87D",
    "accent_blue": "#58A6FF",
    "accent_orange": "#F0883E",
    "accent_red": "#F85149",
    "accent_yellow": "#E3B341",

    # Step type colors
    "step_action": "#A78BFA",      # Purple for actions
    "step_assert": "#34D399",      # Green for assertions
    "step_nav": "#60A5FA",         # Blue for navigation
    "step_wait": "#FBBF24",        # Yellow for waits
    "step_extract": "#F0883E",     # Orange for data extraction

    # Status
    "success": "#3FB950",
    "warning": "#D29922",
    "error": "#F85149",
    "info": "#58A6FF",
}

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

FONTS = {
    "family_ui": "Segoe UI, Inter, system-ui, sans-serif",
    "family_mono": "Cascadia Code, JetBrains Mono, Consolas, monospace",
    "size_xs": "9pt",
    "size_sm": "10pt",
    "size_base": "11pt",
    "size_md": "12pt",
    "size_lg": "14pt",
    "size_xl": "16pt",
    "size_2xl": "20pt",
}

# ---------------------------------------------------------------------------
# Icons (Unicode — can be replaced with SVG later)
# ---------------------------------------------------------------------------

ICONS = {
    "record": "⏺",
    "pause": "⏸",
    "stop": "⏹",
    "inspect": "🔍",
    "play": "▶",
    "settings": "⚙",
    "click": "🖱",
    "type": "⌨",
    "hover": "👆",
    "scroll": "↕",
    "check": "☑",
    "uncheck": "☐",
    "select": "▼",
    "drag": "✥",
    "submit": "⏎",
    "dblclick": "🖱🖱",
    "rightclick": "🖱→",
    "assert": "✓",
    "visible": "👁",
    "hidden": "🙈",
    "enabled": "✅",
    "disabled": "🚫",
    "text": "Aa",
    "url": "🔗",
    "title": "📄",
    "delete": "✕",
    "edit": "✎",
    "duplicate": "⧉",
    "export": "💾",
    "import": "📂",
    "undo": "↩",
    "redo": "↪",
    "search": "🔎",
    "copy": "📋",
    "pom": "📦",
    "workflow": "🔀",
    "code": "📝",
    "nav": "🧭",
    "warning": "⚠",
    "chain": "🔗",
    "force": "⚡",
    "upload": "📁",
    "date": "📅",
    "snapshot": "📸",
    "remove": "⚰️",
    # Data extraction
    "get_text": "📋",
    "get_value": "📋",
    "cast_int": "🔢",
    "cast_float": "🔢",
    "dropdown": "▼",
    "data_type": "🏷",
    "variable": "📦",
    "extract": "📤",
}


# ---------------------------------------------------------------------------
# Main Stylesheet
# ---------------------------------------------------------------------------

def get_stylesheet() -> str:
    """Return the complete QSS dark theme stylesheet."""
    c = COLORS
    f = FONTS
    return f"""
    /* ===================== GLOBAL ===================== */
    QMainWindow, QWidget {{
        background-color: {c['bg_darkest']};
        color: {c['text_primary']};
        font-family: {f['family_ui']};
        font-size: {f['size_base']};
    }}

    /* ===================== BUTTONS ===================== */
    QPushButton {{
        background-color: {c['bg_light']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 16px;
        font-size: {f['size_base']};
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {c['bg_hover']};
        border-color: {c['accent_purple']};
    }}
    QPushButton:pressed {{
        background-color: {c['bg_selected']};
    }}
    QPushButton:disabled {{
        color: {c['text_muted']};
        background-color: {c['bg_dark']};
        border-color: {c['border']};
    }}

    /* Primary accent button */
    QPushButton#primary {{
        background-color: {c['accent_purple']};
        border-color: {c['accent_purple']};
        color: #FFFFFF;
        font-weight: 600;
    }}
    QPushButton#primary:hover {{
        background-color: {c['accent_purple_hover']};
    }}

    /* Success/green button */
    QPushButton#success {{
        background-color: {c['accent_green']}22;
        border: 1px solid {c['accent_green']};
        color: {c['accent_green']};
        font-weight: 600;
    }}
    QPushButton#success:hover {{
        background-color: {c['accent_green']};
        color: {c['bg_darkest']};
    }}

    /* Danger/red button */
    QPushButton#danger {{
        background-color: {c['accent_red']}22;
        border: 1px solid {c['accent_red']};
        color: {c['accent_red']};
        font-weight: 600;
    }}
    QPushButton#danger:hover {{
        background-color: {c['accent_red']};
        color: #FFFFFF;
    }}

    /* Record button (special) */
    QPushButton#record_btn {{
        background-color: {c['accent_red']};
        border: none;
        color: #FFFFFF;
        font-weight: 700;
        font-size: {f['size_md']};
        border-radius: 20px;
        padding: 4px 20px;
    }}
    QPushButton#record_btn:hover {{
        background-color: #FF6B63;
    }}
    QPushButton#record_btn:checked {{
        background-color: {c['accent_red']};
        border: 2px solid #FFFFFF;
    }}

    /* ===================== TAB WIDGET ===================== */
    QTabWidget::pane {{
        background-color: {c['bg_medium']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {c['text_secondary']};
        padding: 10px 20px;
        margin-right: 4px;
        font-weight: 500;
    }}
    QTabBar::tab:selected {{
        color: {c['accent_purple']};
        border-bottom: 2px solid {c['accent_purple']};
    }}
    QTabBar::tab:hover:!selected {{
        color: {c['text_primary']};
        background-color: {c['bg_hover']}44;
    }}

    /* ===================== SCROLL BAR ===================== */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {c['border']};
        border-radius: 5px;
        min-height: 20px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {c['text_muted']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* ===================== COMBO BOX ===================== */
    QComboBox {{
        background-color: {c['bg_medium']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 12px;
    }}
    QComboBox::drop-down {{
        border: none;
    }}

    /* ===================== HUD / POPUP ===================== */
    QWidget#element_popup {{
        background-color: {c['bg_dark']}EE;
        border: 1px solid {c['accent_purple']}88;
        border-radius: 12px;
    }}

    /* ===================== SPLITTER ===================== */
    QSplitter::handle {{
        background-color: {c['border']};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    QSplitter::handle:vertical {{
        height: 2px;
    }}
    QSplitter::handle:hover {{
        background-color: {c['accent_purple']};
    }}

    /* ===================== LABEL ===================== */
    QLabel {{
        color: {c['text_primary']};
    }}
    QLabel#section_header {{
        color: {c['text_secondary']};
        font-size: {f['size_xs']};
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 8px 0 4px 0;
    }}
    QLabel#title {{
        font-size: {f['size_lg']};
        font-weight: 700;
        color: {c['text_primary']};
    }}

    /* ===================== GROUP BOX ===================== */
    QGroupBox {{
        background-color: {c['bg_dark']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 24px 12px 12px 12px;
        margin-top: 24px;
        font-weight: 600;
        color: {c['text_secondary']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        left: 10px;
        top: -8px;
        color: {c['text_secondary']};
        font-size: {f['size_xs']};
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* ===================== LIST WIDGET ===================== */
    QListWidget {{
        background-color: {c['bg_dark']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }}
    QListWidget::item {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px;
        margin: 2px 0;
        color: {c['text_primary']};
    }}
    QListWidget::item:selected {{
        background-color: {c['bg_selected']};
        border-color: {c['accent_purple']};
    }}
    QListWidget::item:hover:!selected {{
        background-color: {c['bg_hover']};
        border-color: {c['border_light']};
    }}

    /* ===================== RADIO / CHECKBOX ===================== */
    QRadioButton, QCheckBox {{
        color: {c['text_primary']};
        spacing: 8px;
        font-size: {f['size_base']};
    }}
    QRadioButton::indicator, QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {c['border_light']};
        border-radius: 3px;
        background-color: {c['bg_medium']};
    }}
    QRadioButton::indicator {{
        border-radius: 9px;
    }}
    QRadioButton::indicator:checked, QCheckBox::indicator:checked {{
        background-color: {c['accent_purple']};
        border-color: {c['accent_purple']};
    }}

    /* ===================== TOOLTIP ===================== */
    QToolTip {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: 6px 10px;
        font-size: {f['size_sm']};
    }}

    /* ===================== STATUS BAR ===================== */
    QStatusBar {{
        background-color: {c['bg_dark']};
        color: {c['text_secondary']};
        border-top: 1px solid {c['border']};
        font-size: {f['size_sm']};
    }}

    /* ===================== DIALOG ===================== */
    QDialog {{
        background-color: {c['bg_dark']};
    }}

    /* ===================== PROGRESS BAR ===================== */
    QProgressBar {{
        background-color: {c['bg_medium']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        height: 4px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {c['accent_purple']};
        border-radius: 4px;
    }}

    /* ===================== HEADER / TOOLBAR AREA ===================== */
    QFrame#toolbar_frame {{
        background-color: {c['bg_dark']};
        border-bottom: 1px solid {c['border']};
        padding: 6px;
    }}
    QFrame#panel_header {{
        background-color: {c['bg_dark']};
        border-bottom: 1px solid {c['border']};
        padding: 8px 12px;
    }}

    /* ===================== CARD FRAME ===================== */
    QFrame#card {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 12px;
    }}
    QFrame#card:hover {{
        border-color: {c['border_light']};
    }}

    /* ===================== MODE TOGGLE ===================== */
    QComboBox#mode_toggle {{
        background-color: {c['accent_purple_dim']}33;
        border: 1px solid {c['accent_purple']}88;
        border-radius: 14px;
        padding: 4px 16px;
        font-size: 11px;
        font-weight: 700;
        color: {c['text_primary']};
        min-width: 100px;
    }}
    QComboBox#mode_toggle:hover {{
        background-color: {c['accent_purple']}44;
        border-color: {c['accent_purple']};
    }}
    QComboBox#mode_toggle::drop-down {{
        border: none;
        width: 20px;
    }}
    QComboBox#mode_toggle QAbstractItemView {{
        background-color: {c['bg_dark']};
        color: {c['text_primary']};
        border: 1px solid {c['accent_purple']};
        border-radius: 8px;
        selection-background-color: {c['accent_purple']};
        outline: none;
    }}

    /* ===================== RECORDING PULSE ===================== */
    QPushButton#record_btn:checked {{
        background-color: {c['accent_red']};
        border: 2px solid #FFFFFF;
    }}
    """
