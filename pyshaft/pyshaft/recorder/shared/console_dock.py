"""PyShaft API Inspector — Console/Output dock for live execution logs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QTextCursor, QColor, QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QProgressBar,
)

from pyshaft.recorder.theme import COLORS, FONTS


class ConsoleSignals(QObject):
    """Thread-safe signals for emitting log messages from worker threads."""
    log_message = pyqtSignal(str, str)  # (message, level)
    run_started = pyqtSignal(str, int)  # (run_name, total_steps)
    step_completed = pyqtSignal(int, str, bool, str)  # (index, step_name, success, details)
    run_finished = pyqtSignal(int, int, float, str)  # (passed, failed, duration_ms, report_path)
    clear_requested = pyqtSignal()


class PyShaftConsole(QWidget):
    """Console panel showing live execution output (used as a tab)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Thread-safe signals
        self.signals = ConsoleSignals()
        self.signals.log_message.connect(self._append_log)
        self.signals.run_started.connect(self._on_run_started)
        self.signals.step_completed.connect(self._on_step_completed)
        self.signals.run_finished.connect(self._on_run_finished)
        self.signals.clear_requested.connect(self.clear)

        self._total_steps = 0
        self._completed_steps = 0
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setStyleSheet(f"background: {COLORS['bg_dark']}; border-bottom: 1px solid {COLORS['border']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)

        title = QLabel("CONSOLE OUTPUT")
        title.setStyleSheet(f"font-weight: 700; font-size: 8pt; color: {COLORS['text_muted']}; letter-spacing: 1.5px;")
        header_layout.addWidget(title)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 9pt;")
        header_layout.addWidget(self._status_label)

        header_layout.addStretch()

        btn_clear = QPushButton("🗑 Clear")
        btn_clear.setFixedHeight(24)
        btn_clear.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {COLORS['text_muted']}; border: none; font-size: 11px; padding: 2px 8px; border-radius: 3px; }}"
            f" QPushButton:hover {{ background: {COLORS['bg_hover']}; color: {COLORS['text_primary']}; }}"
        )
        btn_clear.clicked.connect(self.clear)
        header_layout.addWidget(btn_clear)
        layout.addWidget(header)

        # ── Progress Bar ──
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumHeight(3)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {COLORS['bg_darkest']};
                border: none;
            }}
            QProgressBar::chunk {{
                background: {COLORS['accent_purple']};
            }}
        """)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        # ── Output Area ──
        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setMaximumBlockCount(5000)
        font = QFont(FONTS['family_mono'], 10)
        self._output.setFont(font)
        self._output.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {COLORS['bg_darkest']};
                color: {COLORS['text_primary']};
                border: none;
                padding: 8px;
                selection-background-color: {COLORS['accent_purple']}44;
            }}
        """)
        layout.addWidget(self._output)

    # ── Public API (thread-safe via signals) ──

    def log(self, message: str, level: str = "info") -> None:
        """Thread-safe log a message. Levels: info, success, error, warning, step, header."""
        self.signals.log_message.emit(message, level)

    def log_run_start(self, name: str, total: int) -> None:
        """Signal that a collection/folder run has started."""
        self.signals.run_started.emit(name, total)

    def log_step_result(self, index: int, name: str, success: bool, details: str = "") -> None:
        """Log a single step completion."""
        self.signals.step_completed.emit(index, name, success, details)

    def log_run_finish(self, passed: int, failed: int, duration_ms: float, report_path: str = "") -> None:
        """Signal run completion with summary."""
        self.signals.run_finished.emit(passed, failed, duration_ms, report_path)

    def clear(self) -> None:
        """Clear the console output."""
        self._output.clear()
        self._status_label.setText("")
        self._progress_bar.setVisible(False)

    # ── Slot implementations ──

    def _append_log(self, message: str, level: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        color_map = {
            "info": COLORS['text_secondary'],
            "success": COLORS['accent_green'],
            "error": COLORS['error'],
            "warning": COLORS['accent_orange'],
            "step": COLORS['accent_blue'],
            "header": COLORS['accent_purple'],
            "muted": COLORS['text_muted'],
        }
        color = color_map.get(level, COLORS['text_primary'])

        if level == "header":
            html = f'<span style="color: {COLORS["text_muted"]};">[{timestamp}]</span> <span style="color: {color}; font-weight: bold;">{message}</span>'
        else:
            prefix_map = {
                "success": "✓",
                "error": "✗",
                "warning": "⚠",
                "step": "→",
                "info": "·",
                "muted": " ",
            }
            prefix = prefix_map.get(level, "·")
            html = f'<span style="color: {COLORS["text_muted"]};">[{timestamp}]</span> <span style="color: {color};">{prefix} {message}</span>'

        self._output.appendHtml(html)
        # Auto-scroll to bottom
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._output.setTextCursor(cursor)

    def _on_run_started(self, name: str, total: int) -> None:
        self._total_steps = total
        self._completed_steps = 0
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._status_label.setText(f"Running: {name}")

        self._append_log("", "muted")
        self._append_log(f"{'═' * 60}", "header")
        self._append_log(f"▶ {name}  ({total} request{'s' if total != 1 else ''})", "header")
        self._append_log(f"{'═' * 60}", "header")

    def _on_step_completed(self, index: int, name: str, success: bool, details: str) -> None:
        self._completed_steps = index + 1
        self._progress_bar.setValue(self._completed_steps)
        self._status_label.setText(f"Running: {self._completed_steps}/{self._total_steps}")

        step_num = f"[{index + 1}/{self._total_steps}]"
        if success:
            self._append_log(f"{step_num} {name} {details}", "success")
        else:
            self._append_log(f"{step_num} {name} {details}", "error")

    def _on_run_finished(self, passed: int, failed: int, duration_ms: float, report_path: str) -> None:
        self._progress_bar.setVisible(False)
        total = passed + failed
        duration_s = duration_ms / 1000

        self._append_log(f"{'─' * 60}", "muted")

        if failed == 0:
            self._append_log(f"ALL {total} REQUESTS PASSED  ({duration_s:.1f}s)", "success")
            self._status_label.setText(f"✅ {total} passed ({duration_s:.1f}s)")
            self._status_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 9pt; font-weight: 700;")
        else:
            self._append_log(f"{passed} passed, {failed} FAILED  ({duration_s:.1f}s)", "error")
            self._status_label.setText(f"❌ {failed} failed, {passed} passed ({duration_s:.1f}s)")
            self._status_label.setStyleSheet(f"color: {COLORS['error']}; font-size: 9pt; font-weight: 700;")

        if report_path:
            self._append_log(f"Report: {report_path}", "step")
        self._append_log(f"{'═' * 60}", "muted")
