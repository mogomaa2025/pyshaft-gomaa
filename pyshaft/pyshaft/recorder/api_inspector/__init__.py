"""PyShaft API Inspector — Visual API test builder and code generator.

Launch with: pyshaft inspectapi
"""

from __future__ import annotations

import sys


def run_api_app() -> None:
    """Launch the API Inspector GUI application."""
    import os
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
    from pyshaft.recorder.api_inspector.api_main_window import ApiMainWindow
    from pyshaft.recorder.theme import get_stylesheet

    # Enable High DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    # Modern scaling policy (MUST be called before QApplication)
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QGuiApplication
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
        
    app.setStyleSheet(get_stylesheet())
    window = ApiMainWindow()
    window.show()
    sys.exit(app.exec())
