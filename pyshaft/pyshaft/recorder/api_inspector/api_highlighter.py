"""PyShaft API Inspector — Syntax highlighter for JSON and Python."""

from __future__ import annotations

import re
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor

from pyshaft.recorder.theme import COLORS


class ApiSyntaxHighlighter(QSyntaxHighlighter):
    """Highlighter for JSON (payloads) and Python (code preview)."""

    def __init__(self, parent=None, mode: str = "json") -> None:
        super().__init__(parent)
        self.mode = mode
        self._rules = []

        if mode == "json":
            self._setup_json_rules()
        else:
            self._setup_python_rules()

    def _setup_json_rules(self) -> None:
        # Keywords (null, true, false)
        fmt_kw = QTextCharFormat()
        fmt_kw.setForeground(QColor(COLORS['accent_orange']))
        fmt_kw.setFontWeight(700)
        self._rules.append((QRegularExpression(r"\b(true|false|null)\b"), fmt_kw))

        # Keys
        fmt_key = QTextCharFormat()
        fmt_key.setForeground(QColor(COLORS['accent_purple']))
        self._rules.append((QRegularExpression(r'"[^"\\]*"(?=\s*:)'), fmt_key))

        # String Values
        fmt_str = QTextCharFormat()
        fmt_str.setForeground(QColor(COLORS['accent_green']))
        self._rules.append((QRegularExpression(r':\s*("[^"\\]*")'), fmt_str))

        # Numbers
        fmt_num = QTextCharFormat()
        fmt_num.setForeground(QColor("#DCDCAA"))
        self._rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), fmt_num))

        # Variables {{var}}
        fmt_var = QTextCharFormat()
        fmt_var.setForeground(QColor("#4FC1FF"))
        fmt_var.setBackground(QColor("#264F78"))
        self._rules.append((QRegularExpression(r"\{\{[^}]+\}\}"), fmt_var))

    def _setup_python_rules(self) -> None:
        # Keywords
        fmt_kw = QTextCharFormat()
        fmt_kw.setForeground(QColor("#569CD6"))
        self._rules.append((QRegularExpression(r"\b(def|import|from|return|if|for|in|class|self)\b"), fmt_kw))

        # Methods (api.request)
        fmt_fn = QTextCharFormat()
        fmt_fn.setForeground(QColor("#DCDCAA"))
        self._rules.append((QRegularExpression(r"\.\w+(?=\()"), fmt_fn))

        # Strings
        fmt_str = QTextCharFormat()
        fmt_str.setForeground(QColor(COLORS['accent_green']))
        self._rules.append((QRegularExpression(r'"[^"\\]*"'), fmt_str))
        self._rules.append((QRegularExpression(r"'[^'\\]*'"), fmt_str))

        # Comments
        fmt_com = QTextCharFormat()
        fmt_com.setForeground(QColor(COLORS['text_muted']))
        self._rules.append((QRegularExpression(r"#.*"), fmt_com))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
