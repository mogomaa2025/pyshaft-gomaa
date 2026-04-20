"""PyShaft DriverFactory — creates Chrome, Firefox, or Edge WebDriver instances.

Uses Selenium 4's built-in SeleniumManager for automatic driver discovery.
Falls back to webdriver-manager if SeleniumManager fails.
Configures headless mode, window size, and common stability arguments.
"""

from __future__ import annotations

import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import WebDriver

from pyshaft.config import BrowserType, get_config
from pyshaft.exceptions import DriverCreationError

logger = logging.getLogger("pyshaft.core.driver_factory")

# Common Chrome/Edge arguments for stability in automation
_CHROME_STABILITY_ARGS = [
    "--disable-infobars",
    "--disable-extensions",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-search-engine-choice-screen",
]


class DriverFactory:
    """Factory for creating configured WebDriver instances.

    Reads configuration from ``get_config()`` but allows per-call overrides.
    Uses Selenium 4's built-in SeleniumManager first, then falls back to
    webdriver-manager if needed.

    Usage::

        driver = DriverFactory.create()  # uses config defaults
        driver = DriverFactory.create(browser="firefox", headless=True)
    """

    @staticmethod
    def create(
        browser: str | None = None,
        headless: bool | None = None,
        window_size: str | None = None,
    ) -> WebDriver:
        """Create a WebDriver instance with the given or configured settings.

        Args:
            browser: Browser name override (chrome/firefox/edge).
            headless: Headless mode override.
            window_size: Window size override (e.g., "1920x1080").

        Returns:
            A configured WebDriver instance.

        Raises:
            DriverCreationError: If the browser driver cannot be created.
        """
        config = get_config()
        browser = browser or config.browser.browser
        headless = headless if headless is not None else config.browser.headless
        window_size = window_size or config.browser.window_size

        logger.info("Creating %s driver (headless=%s, size=%s)", browser, headless, window_size)

        match browser:
            case BrowserType.CHROME:
                return DriverFactory._create_chrome(headless, window_size)
            case BrowserType.FIREFOX:
                return DriverFactory._create_firefox(headless, window_size)
            case BrowserType.EDGE:
                return DriverFactory._create_edge(headless, window_size)
            case _:
                raise DriverCreationError(browser, f"Unsupported browser: {browser!r}")

    @staticmethod
    def _create_chrome(headless: bool, window_size: str) -> WebDriver:
        """Create a Chrome WebDriver instance."""
        options = ChromeOptions()

        for arg in _CHROME_STABILITY_ARGS:
            options.add_argument(arg)

        if headless:
            options.add_argument("--headless=new")

        width, height = _parse_window_size(window_size)
        options.add_argument(f"--window-size={width},{height}")

        # Try Selenium's built-in manager first (no network download needed
        # if driver is already cached or browser includes it)
        try:
            driver = webdriver.Chrome(options=options)
            _configure_timeouts(driver)
            logger.info("Chrome driver created via SeleniumManager")
            return driver
        except Exception as e1:
            logger.debug("SeleniumManager failed: %s — trying webdriver-manager", e1)

        # Fallback to webdriver-manager
        try:
            from webdriver_manager.chrome import ChromeDriverManager

            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            _configure_timeouts(driver)
            logger.info("Chrome driver created via webdriver-manager")
            return driver
        except Exception as e2:
            raise DriverCreationError("chrome", str(e2)) from e2

    @staticmethod
    def _create_firefox(headless: bool, window_size: str) -> WebDriver:
        """Create a Firefox WebDriver instance."""
        options = FirefoxOptions()

        if headless:
            options.add_argument("--headless")

        # Try Selenium's built-in manager first
        try:
            driver = webdriver.Firefox(options=options)
            width, height = _parse_window_size(window_size)
            driver.set_window_size(width, height)
            _configure_timeouts(driver)
            logger.info("Firefox driver created via SeleniumManager")
            return driver
        except Exception as e1:
            logger.debug("SeleniumManager failed: %s — trying webdriver-manager", e1)

        # Fallback to webdriver-manager
        try:
            from webdriver_manager.firefox import GeckoDriverManager

            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
            width, height = _parse_window_size(window_size)
            driver.set_window_size(width, height)
            _configure_timeouts(driver)
            logger.info("Firefox driver created via webdriver-manager")
            return driver
        except Exception as e2:
            raise DriverCreationError("firefox", str(e2)) from e2

    @staticmethod
    def _create_edge(headless: bool, window_size: str) -> WebDriver:
        """Create an Edge WebDriver instance."""
        options = EdgeOptions()

        for arg in _CHROME_STABILITY_ARGS:
            options.add_argument(arg)

        if headless:
            options.add_argument("--headless=new")

        width, height = _parse_window_size(window_size)
        options.add_argument(f"--window-size={width},{height}")

        # Try Selenium's built-in manager first
        try:
            driver = webdriver.Edge(options=options)
            _configure_timeouts(driver)
            logger.info("Edge driver created via SeleniumManager")
            return driver
        except Exception as e1:
            logger.debug("SeleniumManager failed: %s — trying webdriver-manager", e1)

        # Fallback to webdriver-manager
        try:
            from webdriver_manager.microsoft import EdgeChromiumDriverManager

            service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=options)
            _configure_timeouts(driver)
            logger.info("Edge driver created via webdriver-manager")
            return driver
        except Exception as e2:
            raise DriverCreationError("edge", str(e2)) from e2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_window_size(size: str) -> tuple[int, int]:
    """Parse 'WIDTHxHEIGHT' string into (width, height) tuple."""
    parts = size.lower().split("x")
    return int(parts[0].strip()), int(parts[1].strip())


def _configure_timeouts(driver: WebDriver) -> None:
    """Set page load and script timeouts from config."""
    config = get_config()
    nav_timeout = config.browser.navigation_timeout
    driver.set_page_load_timeout(nav_timeout)
    driver.set_script_timeout(nav_timeout)
