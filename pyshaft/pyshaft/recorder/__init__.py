"""PyShaft Recorder — GUI-based test recorder and inspector.

Launch via:
    pyshaft inspect
    pyshaft record
    pyshaft-recorder
"""

__all__ = ["main"]


def main():
    """Entry point for the recorder GUI."""
    from pyshaft.recorder.app import run_app
    run_app()
