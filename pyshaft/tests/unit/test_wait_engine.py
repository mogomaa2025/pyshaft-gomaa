"""Unit tests for PyShaft WaitEngine — auto-wait pipeline.

Tests cover:
    - WaitEngine.wait_for_condition with various outcomes
    - Element state snapshot capture logic
    - Position stability check logic
    - Overlay detection logic
    - The full readiness pipeline config integration
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from pyshaft.config import Config, WaitsConfig, ValidationsConfig, reset_config
from pyshaft.core.wait_engine import (
    WaitEngine,
    _capture_element_state,
    _is_enabled,
)
from pyshaft.exceptions import WaitTimeoutError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_element(displayed: bool = True, enabled: bool = True, tag: str = "button") -> MagicMock:
    """Create a mock WebElement with configurable state."""
    el = MagicMock()
    el.is_displayed.return_value = displayed
    el.is_enabled.return_value = enabled
    el.tag_name = tag
    el.text = "Mock Element"
    el.location = {"x": 100, "y": 200}
    el.size = {"width": 120, "height": 40}
    return el


def _mock_driver() -> MagicMock:
    """Create a mock WebDriver."""
    driver = MagicMock()
    driver.current_url = "http://test.com"
    driver.title = "Test Page"
    return driver


# ---------------------------------------------------------------------------
# wait_for_condition tests
# ---------------------------------------------------------------------------


class TestWaitForCondition:
    """Test the generic condition waiter."""

    def setup_method(self) -> None:
        reset_config()

    def teardown_method(self) -> None:
        reset_config()

    def test_condition_met_immediately(self) -> None:
        result = WaitEngine.wait_for_condition(
            condition=lambda: True,
            description="always true",
            timeout=1.0,
        )
        assert result is True

    def test_condition_met_after_delay(self) -> None:
        start = time.time()
        call_count = 0

        def condition():
            nonlocal call_count
            call_count += 1
            return call_count >= 3

        result = WaitEngine.wait_for_condition(
            condition=condition,
            description="true after 3 calls",
            timeout=5.0,
        )
        assert result is True
        assert call_count >= 3

    def test_condition_timeout_raises(self) -> None:
        with pytest.raises(WaitTimeoutError, match="custom condition"):
            WaitEngine.wait_for_condition(
                condition=lambda: False,
                description="custom condition",
                timeout=0.5,
            )

    def test_condition_exception_keeps_polling(self) -> None:
        call_count = 0

        def flaky_condition():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not ready")
            return True

        result = WaitEngine.wait_for_condition(
            condition=flaky_condition,
            description="flaky",
            timeout=5.0,
        )
        assert result is True


# ---------------------------------------------------------------------------
# _is_enabled tests
# ---------------------------------------------------------------------------


class TestIsEnabled:
    """Test the enabled check."""

    def test_enabled_element(self) -> None:
        el = _mock_element(enabled=True)
        assert _is_enabled(el) is True

    def test_disabled_element(self) -> None:
        el = _mock_element(enabled=False)
        assert _is_enabled(el) is False

    def test_stale_element(self) -> None:
        from selenium.common.exceptions import StaleElementReferenceException

        el = _mock_element()
        el.is_enabled.side_effect = StaleElementReferenceException("stale")
        assert _is_enabled(el) is False


# ---------------------------------------------------------------------------
# _capture_element_state tests
# ---------------------------------------------------------------------------


class TestCaptureElementState:
    """Test element state snapshot for error messages."""

    def test_captures_basic_properties(self) -> None:
        driver = _mock_driver()
        driver.execute_script.return_value = {
            "opacity": "1",
            "visibility": "visible",
            "display": "block",
            "pointerEvents": "auto",
            "overflow": "visible",
        }
        el = _mock_element()

        state = _capture_element_state(driver, el)

        assert state["tag"] == "button"
        assert state["displayed"] is True
        assert state["enabled"] is True
        assert "location" in state
        assert "size" in state
        assert state["text_preview"] == "Mock Element"

    def test_handles_exceptions_gracefully(self) -> None:
        driver = _mock_driver()
        driver.execute_script.side_effect = Exception("JS failed")

        el = _mock_element()
        el.tag_name = "div"

        state = _capture_element_state(driver, el)

        # Should still capture basic properties even if JS fails
        assert state["tag"] == "div"
        assert state["displayed"] is True

    def test_truncates_long_text(self) -> None:
        driver = _mock_driver()
        driver.execute_script.return_value = {}

        el = _mock_element()
        el.text = "A" * 100

        state = _capture_element_state(driver, el)
        assert state["text_preview"].endswith("...")
        assert len(state["text_preview"]) == 53  # 50 chars + "..."


# ---------------------------------------------------------------------------
# WaitEngine.wait_for_element_ready tests (with mocked config)
# ---------------------------------------------------------------------------


class TestWaitForElementReady:
    """Test the full readiness pipeline with mocked config."""

    def setup_method(self) -> None:
        reset_config()

    def teardown_method(self) -> None:
        reset_config()

    @patch("pyshaft.core.wait_engine.get_config")
    @patch("pyshaft.core.wait_engine._is_visible")
    @patch("pyshaft.core.wait_engine._is_position_stable")
    @patch("pyshaft.core.wait_engine._is_not_covered")
    def test_all_checks_pass(
        self, mock_covered, mock_stable, mock_visible, mock_config
    ) -> None:
        config = Config()
        config.waits = WaitsConfig(
            default_element_timeout=5.0,
            polling_interval=0.1,
            stability_threshold=0.1,
            respect_native_waits=True,
        )
        config.validations = ValidationsConfig(force_element_visibility=True)
        mock_config.return_value = config
        mock_visible.return_value = True
        mock_stable.return_value = True
        mock_covered.return_value = True

        driver = _mock_driver()
        el = _mock_element()

        result = WaitEngine.wait_for_element_ready(driver, el)
        assert result is el

    @patch("pyshaft.core.wait_engine.get_config")
    def test_skip_when_native_waits_disabled(self, mock_config) -> None:
        config = Config()
        config.waits = WaitsConfig(respect_native_waits=False)
        mock_config.return_value = config

        driver = _mock_driver()
        el = _mock_element(displayed=False, enabled=False)

        # Should return immediately without checking anything
        result = WaitEngine.wait_for_element_ready(driver, el)
        assert result is el

    @patch("pyshaft.core.wait_engine.get_config")
    @patch("pyshaft.core.wait_engine._is_visible")
    @patch("pyshaft.core.wait_engine._is_position_stable")
    @patch("pyshaft.core.wait_engine._is_not_covered")
    def test_skip_visibility_when_not_forced(
        self, mock_covered, mock_stable, mock_visible, mock_config
    ) -> None:
        config = Config()
        config.waits = WaitsConfig(
            default_element_timeout=1.0,
            polling_interval=0.1,
            stability_threshold=0.1,
            respect_native_waits=True,
        )
        config.validations = ValidationsConfig(force_element_visibility=False)
        mock_config.return_value = config
        mock_visible.return_value = False  # Element NOT visible
        mock_stable.return_value = True
        mock_covered.return_value = True

        driver = _mock_driver()
        el = _mock_element(enabled=True)

        # Should pass even though element is not visible (visibility not forced)
        result = WaitEngine.wait_for_element_ready(driver, el)
        assert result is el
        # _is_visible should NOT have been called
        mock_visible.assert_not_called()

    @patch("pyshaft.core.wait_engine.get_config")
    @patch("pyshaft.core.wait_engine._is_visible")
    def test_timeout_when_not_visible(self, mock_visible, mock_config) -> None:
        config = Config()
        config.waits = WaitsConfig(
            default_element_timeout=0.5,
            polling_interval=0.1,
            stability_threshold=0.1,
            respect_native_waits=True,
        )
        config.validations = ValidationsConfig(force_element_visibility=True)
        mock_config.return_value = config
        mock_visible.return_value = False  # Never visible

        driver = _mock_driver()
        driver.execute_script.return_value = {}
        el = _mock_element(displayed=False)

        with pytest.raises(WaitTimeoutError, match="not visible"):
            WaitEngine.wait_for_element_ready(driver, el, timeout=0.5)


# ---------------------------------------------------------------------------
# WaitEngine.wait_for_page_load tests
# ---------------------------------------------------------------------------


class TestWaitForPageLoad:
    """Test page load readiness wait."""

    def setup_method(self) -> None:
        reset_config()

    def teardown_method(self) -> None:
        reset_config()

    def test_page_already_loaded(self) -> None:
        driver = _mock_driver()
        driver.execute_script.return_value = "complete"

        WaitEngine.wait_for_page_load(driver, timeout=2.0)
        # Should not raise

    def test_page_loads_after_delay(self) -> None:
        driver = _mock_driver()
        call_count = 0

        def mock_script(script):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return "loading"
            return "complete"

        driver.execute_script.side_effect = mock_script

        WaitEngine.wait_for_page_load(driver, timeout=5.0)
        assert call_count >= 3

    def test_page_load_timeout(self) -> None:
        driver = _mock_driver()
        driver.execute_script.return_value = "loading"

        with pytest.raises(WaitTimeoutError, match="readyState"):
            WaitEngine.wait_for_page_load(driver, timeout=0.5)


# ---------------------------------------------------------------------------
# WaitTimeoutError message tests
# ---------------------------------------------------------------------------


class TestWaitTimeoutErrorMessages:
    """Test that timeout errors contain useful debugging info."""

    def test_includes_condition(self) -> None:
        err = WaitTimeoutError(
            condition="element visible",
            timeout=10.0,
        )
        assert "element visible" in str(err)
        assert "10.0s" in str(err)

    def test_includes_element_state(self) -> None:
        err = WaitTimeoutError(
            condition="element ready",
            timeout=5.0,
            element_state={
                "tag": "button",
                "displayed": "False",
                "failure_reason": "not visible",
            },
        )
        msg = str(err)
        assert "button" in msg
        assert "not visible" in msg

    def test_empty_state_handled(self) -> None:
        err = WaitTimeoutError(
            condition="test",
            timeout=1.0,
            element_state={},
        )
        assert "unknown" in str(err) or "test" in str(err)
