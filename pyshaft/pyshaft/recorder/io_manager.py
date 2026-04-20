"""PyShaft Recorder — Import/Export Manager.

Handles saving/loading recording sessions and exporting generated code.
"""

from __future__ import annotations

import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path

from pyshaft.recorder.models import RecordingSession

logger = logging.getLogger("pyshaft.recorder.io_manager")

# Default save directory
_RECORDINGS_DIR = Path.home() / ".pyshaft" / "recordings"


class IOManager:
    """Manages import/export of recording sessions and generated code."""

    @staticmethod
    def get_recordings_dir() -> Path:
        """Get (and create) the recordings directory."""
        _RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        return _RECORDINGS_DIR

    # -------------------------------------------------------------------------
    # Session Files (.pyshaft)
    # -------------------------------------------------------------------------

    @staticmethod
    def save_session(session: RecordingSession, path: str | Path | None = None) -> Path:
        """Save a recording session to a .pyshaft JSON file.

        Args:
            session: The session to save.
            path: File path. If None, auto-generates in the recordings dir.

        Returns:
            Path to the saved file.
        """
        if path is None:
            recordings_dir = IOManager.get_recordings_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c if c.isalnum() else "_" for c in session.name)
            filename = f"{safe_name}_{timestamp}.pyshaft"
            path = recordings_dir / filename

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        import time
        session.modified_at = time.time()

        path.write_text(session.to_json(), encoding="utf-8")
        logger.info("Session saved to %s", path)
        return path

    @staticmethod
    def load_session(path: str | Path) -> RecordingSession:
        """Load a recording session from a .pyshaft file.

        Args:
            path: Path to the .pyshaft file.

        Returns:
            The loaded RecordingSession.
        """
        path = Path(path)
        json_str = path.read_text(encoding="utf-8")
        session = RecordingSession.from_json(json_str)
        logger.info("Session loaded from %s (%d steps)", path, len(session.steps))
        return session

    # -------------------------------------------------------------------------
    # Python Code Export (.py)
    # -------------------------------------------------------------------------

    @staticmethod
    def export_code(
        session: RecordingSession,
        path: str | Path,
        mode: str = "flat",
    ) -> Path:
        """Export generated PyShaft test code to a .py file.

        Args:
            session: The recording session.
            path: Output file path.
            mode: Code generation mode ("flat" or "chain").

        Returns:
            Path to the exported file.
        """
        from pyshaft.recorder.code_generator import generate_code

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        code = generate_code(session, mode=mode)
        path.write_text(code, encoding="utf-8")
        logger.info("Code exported to %s", path)
        return path

    @staticmethod
    def get_recent_files(limit: int = 10) -> list[Path]:
        """Get the most recently modified .pyshaft files.

        Args:
            limit: Maximum number of files to return.

        Returns:
            List of file paths, most recent first.
        """
        recordings_dir = IOManager.get_recordings_dir()
        files = sorted(
            recordings_dir.glob("*.pyshaft"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        return files[:limit]

    @staticmethod
    def get_auto_save_path(session_name: str) -> Path:
        """Get the auto-save path for a session."""
        recordings_dir = IOManager.get_recordings_dir()
        safe_name = "".join(c if c.isalnum() else "_" for c in session_name)
        return recordings_dir / f"_autosave_{safe_name}.pyshaft"
