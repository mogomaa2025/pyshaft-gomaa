"""PyShaft session management — thread-local driver storage for parallel safety.

SessionContext holds the WebDriver instance in thread-local storage so that
each pytest-xdist worker gets its own isolated browser session.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

from pyshaft.exceptions import SessionNotActiveError

logger = logging.getLogger("pyshaft.session")


class SessionContext:
    """Thread-safe WebDriver session storage.

    Each thread (pytest-xdist worker) gets its own driver instance via
    ``threading.local()``. The session tracks state, browser name, and timing.

    Usage::

        session_context.start(driver)
        driver = session_context.driver
        session_context.close()
    """

    _local = threading.local()
    _lock = threading.Lock()
    _all_drivers: list[WebDriver] = []

    @property
    def driver(self) -> WebDriver:
        """Get the active WebDriver for the current thread.

        Raises:
            SessionNotActiveError: If no driver has been started.
        """
        drv = getattr(self._local, "driver", None)
        if drv is None:
            raise SessionNotActiveError()
        return drv

    @property
    def is_active(self) -> bool:
        """Check if a driver session is active for the current thread."""
        return getattr(self._local, "driver", None) is not None

    @property
    def browser_name(self) -> str:
        """Get the browser name for the current session."""
        return getattr(self._local, "browser_name", "unknown")

    @property
    def start_time(self) -> float:
        """Get the session start timestamp."""
        return getattr(self._local, "start_time", 0.0)

    def start(self, driver: WebDriver, browser_name: str = "chrome") -> None:
        """Register a WebDriver instance for the current thread.

        Args:
            driver: The WebDriver instance to store.
            browser_name: Name of the browser (for logging).
        """
        self._local.driver = driver
        self._local.browser_name = browser_name
        self._local.start_time = time.time()

        with self._lock:
            self._all_drivers.append(driver)

        logger.info(
            "Session started: %s (thread=%s)",
            browser_name,
            threading.current_thread().name,
        )

    def close(self) -> None:
        """Close the WebDriver for the current thread and clear state."""
        drv = getattr(self._local, "driver", None)
        if drv is None:
            return

        browser = self.browser_name
        try:
            drv.quit()
            logger.info("Session closed: %s", browser)
        except Exception as e:
            logger.warning("Error closing session: %s", e)
        finally:
            with self._lock:
                if drv in self._all_drivers:
                    self._all_drivers.remove(drv)
            self._local.driver = None
            self._local.browser_name = None
            self._local.start_time = None

    def close_all(self) -> None:
        """Close all WebDriver instances across all threads.

        Used during pytest session teardown to ensure no browser leaks.
        """
        with self._lock:
            drivers = list(self._all_drivers)
            self._all_drivers.clear()

        for drv in drivers:
            try:
                drv.quit()
            except Exception as e:
                logger.warning("Error closing driver in close_all: %s", e)

        # Clear local thread state
        self._local.driver = None
        self._local.browser_name = None
        self._local.start_time = None
        logger.info("All sessions closed")


# Module-level singleton
session_context = SessionContext()
