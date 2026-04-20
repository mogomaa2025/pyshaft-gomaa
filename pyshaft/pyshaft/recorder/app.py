"""PyShaft Recorder — Application entry point.

Launch the recorder GUI:
    pyshaft inspect            # inspector-first mode (default)
    pyshaft inspect --url URL  # inspector with start URL
    pyshaft record             # auto-capture recording mode
    pyshaft-recorder           # standalone entry point
    python -m pyshaft.recorder
"""

from __future__ import annotations

import sys
import logging


def run_app(url: str | None = None, mode: str = "inspect"):
    """Launch the PyShaft Recorder GUI application.

    Args:
        url: Optional start URL to open in the browser.
        mode: 'inspect' for inspector-first, 'record' for auto-capture.
    """
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont, QIcon
        from PyQt6.QtCore import Qt
    except ImportError:
        print(
            "PyQt6 is required for the recorder GUI.\n"
            "Install it with: pip install pyshaft[recorder]\n"
            "Or: pip install PyQt6"
        )
        sys.exit(1)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Important: QtWebEngineWidgets must be imported before QApplication
    try:
        from PyQt6 import QtWebEngineWidgets
    except ImportError:
        print("PyQt6-WebEngine is required for the recorder GUI.")
        print("Install with: pip install PyQt6-WebEngine")
        sys.exit(1)

    # Set OpenGL sharing attribute as recommended by the error message
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("PyShaft Recorder")
    app.setApplicationDisplayName("PyShaft Recorder")
    app.setOrganizationName("PyShaft")

    # Apply dark theme
    from pyshaft.recorder.theme import get_stylesheet
    app.setStyleSheet(get_stylesheet())

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Create and show main window
    from pyshaft.recorder.main_window import MainWindow
    window = MainWindow(start_mode=mode)

    if url:
        window._url_bar.setText(url)

    window.show()

    sys.exit(app.exec())


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="pyshaft-recorder",
        description="PyShaft Recorder — Record and generate test code",
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        default=None,
        help="Start URL to open in the browser",
    )
    parser.add_argument(
        "--browser", "-b",
        type=str,
        default="chrome",
        choices=["chrome", "edge"],
        help="Browser to use (default: chrome)",
    )

    args = parser.parse_args()
    run_app(url=args.url)


if __name__ == "__main__":
    main()
