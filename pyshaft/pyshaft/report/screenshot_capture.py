"""PyShaft Report — Enhanced screenshot capture for per-step screenshots."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from pyshaft.config import get_config
from pyshaft.session import session_context

logger = logging.getLogger("pyshaft.report.screenshot_capture")


class ScreenshotCapture:
    """Captures screenshots at key points during test execution.

    Usage::

        capture = ScreenshotCapture()
        path = capture.capture_step("test_login", 0, "click_login_button")
        path = capture.capture_failure("test_login")
    """

    def __init__(self, output_dir: str | Path | None = None) -> None:
        config = get_config()
        self._output_dir = Path(output_dir or config.report.output_dir) / "screenshots"
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def capture_step(
        self,
        test_name: str,
        step_index: int,
        label: str = "",
    ) -> str | None:
        """Capture a screenshot for a test step.

        Args:
            test_name: Name of the current test.
            step_index: Index of the step (0-based).
            label: Optional label for the screenshot file.

        Returns:
            Path to the saved screenshot, or None on failure.
        """
        if not session_context.is_active:
            return None

        safe_name = _sanitize(test_name)
        safe_label = _sanitize(label) if label else f"step_{step_index:03d}"
        filename = f"{safe_name}_{safe_label}.png"
        path = self._output_dir / filename

        try:
            session_context.driver.save_screenshot(str(path))
            logger.debug("Step screenshot saved: %s", path)
            return str(path)
        except Exception as e:
            logger.warning("Failed to capture step screenshot: %s", e)
            return None

    def capture_failure(self, test_name: str) -> str | None:
        """Capture a screenshot on test failure.

        Args:
            test_name: Name of the failed test.

        Returns:
            Path to the saved screenshot, or None on failure.
        """
        if not session_context.is_active:
            return None

        safe_name = _sanitize(test_name)
        filename = f"{safe_name}_FAILURE_{int(time.time())}.png"
        path = self._output_dir / filename

        try:
            session_context.driver.save_screenshot(str(path))
            logger.info("Failure screenshot saved: %s", path)
            return str(path)
        except Exception as e:
            logger.warning("Failed to capture failure screenshot: %s", e)
            return None

    @property
    def screenshots_dir(self) -> Path:
        return self._output_dir


def _sanitize(name: str) -> str:
    """Sanitize a name for use as a filename."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:80]
