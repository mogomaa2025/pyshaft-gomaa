"""PyShaft WaitEngine — Playwright-grade auto-wait pipeline.

Every web action silently passes through this pipeline before execution:
    1. Element exists in DOM
    2. Element is visible (not display:none, not opacity:0, not zero-size)
    3. Element is enabled (no disabled attribute)
    4. Position is stable (not mid-animation — position unchanged for stability_threshold)
    5. Not covered by overlay/modal (elementFromPoint check)

The pipeline is fully configurable via pyshaft.toml:
    - ``respect_native_waits = false`` → skip entire pipeline (raw Selenium)
    - ``force_element_visibility = false`` → skip visibility check
    - ``stability_threshold = 0.3`` → 300ms position stability window
    - ``default_element_timeout = 10`` → max wait time per check
    - ``polling_interval = 0.25`` → check every 250ms

Timeout errors include a full element state snapshot for debugging.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from selenium.common.exceptions import (
    JavascriptException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from pyshaft.config import get_config
from pyshaft.exceptions import ElementNotInteractableError, WaitTimeoutError

logger = logging.getLogger("pyshaft.core.wait_engine")


# ---------------------------------------------------------------------------
# Element state snapshot — used in timeout error messages
# ---------------------------------------------------------------------------


def _capture_element_state(driver: WebDriver, element: WebElement) -> dict[str, Any]:
    """Capture a comprehensive snapshot of an element's current state.

    Used for rich error messages when wait conditions time out.

    Returns:
        Dict with keys: tag, displayed, enabled, location, size,
        opacity, visibility, overflow, covered_by, text_preview.
    """
    state: dict[str, Any] = {}

    try:
        state["tag"] = element.tag_name
    except Exception:
        state["tag"] = "unknown"

    try:
        state["displayed"] = element.is_displayed()
    except Exception:
        state["displayed"] = "error"

    try:
        state["enabled"] = element.is_enabled()
    except Exception:
        state["enabled"] = "error"

    try:
        state["location"] = element.location
    except Exception:
        state["location"] = "unknown"

    try:
        state["size"] = element.size
    except Exception:
        state["size"] = "unknown"

    # CSS computed properties via JS
    try:
        css_state = driver.execute_script("""
            var el = arguments[0];
            var cs = window.getComputedStyle(el);
            return {
                opacity: cs.opacity,
                visibility: cs.visibility,
                display: cs.display,
                pointerEvents: cs.pointerEvents,
                overflow: cs.overflow
            };
        """, element)
        state.update(css_state or {})
    except Exception:
        pass

    # Text preview (first 50 chars)
    try:
        text = element.text or ""
        state["text_preview"] = text[:50] + ("..." if len(text) > 50 else "")
    except Exception:
        state["text_preview"] = ""

    return state


# ---------------------------------------------------------------------------
# Individual wait checks
# ---------------------------------------------------------------------------


def _is_visible(driver: WebDriver, element: WebElement) -> bool:
    """Check if an element is truly visible.

    Goes beyond Selenium's is_displayed() by also checking:
        - CSS opacity > 0
        - CSS visibility != 'hidden'
        - Element has non-zero dimensions
        - CSS display != 'none'
    """
    try:
        if not element.is_displayed():
            return False

        result = driver.execute_script("""
            var el = arguments[0];
            var cs = window.getComputedStyle(el);
            var rect = el.getBoundingClientRect();

            if (cs.display === 'none') return false;
            if (cs.visibility === 'hidden') return false;
            if (parseFloat(cs.opacity) === 0) return false;
            if (rect.width === 0 && rect.height === 0) return false;

            return true;
        """, element)

        return bool(result)

    except (StaleElementReferenceException, NoSuchElementException):
        return False
    except Exception:
        # Fallback to basic check if JS fails
        try:
            return element.is_displayed()
        except Exception:
            return False


def _is_enabled(element: WebElement) -> bool:
    """Check if an element is enabled (no disabled attribute)."""
    try:
        return element.is_enabled()
    except (StaleElementReferenceException, NoSuchElementException):
        return False


def _is_position_stable(
    driver: WebDriver,
    element: WebElement,
    stability_threshold: float,
    poll_interval: float = 0.05,
) -> bool:
    """Check if an element's position has been stable for the threshold duration.

    Compares the element's bounding rect at two points separated by
    stability_threshold seconds. If position hasn't changed, it's stable.

    This detects:
        - CSS animations in progress
        - JavaScript-driven transitions
        - Layout shifts from lazy-loaded content
    """
    try:
        rect1 = driver.execute_script("""
            var rect = arguments[0].getBoundingClientRect();
            return {top: rect.top, left: rect.left, width: rect.width, height: rect.height};
        """, element)

        if not rect1:
            return False

        time.sleep(stability_threshold)

        rect2 = driver.execute_script("""
            var rect = arguments[0].getBoundingClientRect();
            return {top: rect.top, left: rect.left, width: rect.width, height: rect.height};
        """, element)

        if not rect2:
            return False

        # Compare positions (allow 1px tolerance for sub-pixel rendering)
        return (
            abs(rect1["top"] - rect2["top"]) <= 1
            and abs(rect1["left"] - rect2["left"]) <= 1
            and abs(rect1["width"] - rect2["width"]) <= 1
            and abs(rect1["height"] - rect2["height"]) <= 1
        )

    except (StaleElementReferenceException, NoSuchElementException):
        return False
    except Exception as e:
        logger.debug("Position stability check failed: %s", e)
        return True  # Assume stable if we can't check


def _is_not_covered(driver: WebDriver, element: WebElement) -> bool:
    """Check if an element is not covered by another element (overlay/modal).

    Uses document.elementFromPoint() at the element's center to detect
    overlapping elements like modals, tooltips, loading spinners, etc.

    Returns True if the element (or a child of it) is the topmost at its center.
    """
    try:
        result = driver.execute_script("""
            var el = arguments[0];
            var rect = el.getBoundingClientRect();

            // Get the center point of the element
            var cx = rect.left + rect.width / 2;
            var cy = rect.top + rect.height / 2;

            // Check if the point is within the viewport
            if (cx < 0 || cy < 0 ||
                cx > window.innerWidth || cy > window.innerHeight) {
                // Element is outside viewport — scroll into view first
                el.scrollIntoView({block: 'center', inline: 'center'});
                rect = el.getBoundingClientRect();
                cx = rect.left + rect.width / 2;
                cy = rect.top + rect.height / 2;
            }

            var topEl = document.elementFromPoint(cx, cy);

            // Check if the top element IS the target or is INSIDE the target
            if (!topEl) return {covered: false, by: null};
            if (topEl === el) return {covered: false, by: null};
            if (el.contains(topEl)) return {covered: false, by: null};

            // Element is covered — gather info about the covering element
            return {
                covered: true,
                by: {
                    tag: topEl.tagName.toLowerCase(),
                    id: topEl.id || null,
                    className: topEl.className || null,
                    text: (topEl.textContent || '').substring(0, 50)
                }
            };
        """, element)

        if not result:
            return True

        if result.get("covered"):
            cover_info = result.get("by", {})
            logger.debug(
                "Element is covered by <%s id=%r class=%r>",
                cover_info.get("tag", "?"),
                cover_info.get("id", ""),
                cover_info.get("className", ""),
            )
            return False

        return True

    except (StaleElementReferenceException, NoSuchElementException):
        return False
    except Exception as e:
        logger.debug("Cover check failed: %s — assuming not covered", e)
        return True


def _get_covering_element_info(driver: WebDriver, element: WebElement) -> str | None:
    """Get a description of the element covering the target, if any."""
    try:
        result = driver.execute_script("""
            var el = arguments[0];
            var rect = el.getBoundingClientRect();
            var cx = rect.left + rect.width / 2;
            var cy = rect.top + rect.height / 2;
            var topEl = document.elementFromPoint(cx, cy);

            if (!topEl || topEl === el || el.contains(topEl)) return null;

            var desc = '<' + topEl.tagName.toLowerCase();
            if (topEl.id) desc += ' id="' + topEl.id + '"';
            if (topEl.className) desc += ' class="' + topEl.className + '"';
            desc += '>';
            return desc;
        """, element)
        return result
    except Exception:
        return None


# ---------------------------------------------------------------------------
# WaitEngine — main pipeline
# ---------------------------------------------------------------------------


class WaitEngine:
    """Auto-wait engine — ensures elements are actionable before interaction.

    The full pipeline checks (in order):
        1. Element is visible (CSS + dimensions)
        2. Element is enabled (no disabled attr)
        3. Position is stable (not mid-animation)
        4. Not covered by overlay/modal

    When ``respect_native_waits`` is False, all checks are skipped.
    When ``force_element_visibility`` is False, step 1 is skipped.
    """

    @staticmethod
    def wait_for_element_ready(
        driver: WebDriver,
        element: WebElement,
        timeout: float | None = None,
        check_visibility: bool | None = None,
        check_stability: bool = True,
        check_overlay: bool = True,
    ) -> WebElement:
        """Wait for an element to be fully ready for interaction.

        This is the main entry point called by the action pipeline.

        Args:
            driver: The WebDriver instance.
            element: The WebElement to wait for.
            timeout: Max wait time in seconds (defaults to config).
            check_visibility: Override for visibility check (defaults to config).
            check_stability: Whether to check position stability.
            check_overlay: Whether to check for covering overlays.

        Returns:
            The element once all readiness checks pass.

        Raises:
            WaitTimeoutError: If any check doesn't pass within timeout.
            ElementNotInteractableError: If element is covered by overlay.
        """
        config = get_config()

        # Skip entire pipeline if native waits are disabled
        if not config.waits.respect_native_waits:
            return element

        timeout = timeout or config.waits.default_element_timeout
        poll = config.waits.polling_interval
        stability = config.waits.stability_threshold
        do_visibility = (
            check_visibility if check_visibility is not None
            else config.validations.force_element_visibility
        )

        deadline = time.time() + timeout
        last_state: dict[str, Any] = {}
        last_failure_reason = ""

        while time.time() < deadline:
            try:
                # Check 1: Visibility
                if do_visibility and not _is_visible(driver, element):
                    last_failure_reason = "not visible"
                    time.sleep(poll)
                    continue

                # Check 2: Enabled
                if not _is_enabled(element):
                    last_failure_reason = "disabled"
                    time.sleep(poll)
                    continue

                # Check 3: Position stability
                if check_stability and not _is_position_stable(driver, element, stability):
                    last_failure_reason = "position unstable (animating)"
                    # Don't sleep — stability check already waited stability_threshold
                    continue

                # Check 4: Not covered by overlay
                if check_overlay and not _is_not_covered(driver, element):
                    cover_info = _get_covering_element_info(driver, element)
                    last_failure_reason = f"covered by overlay: {cover_info or 'unknown'}"
                    time.sleep(poll)
                    continue

                # All checks passed
                return element

            except StaleElementReferenceException:
                last_failure_reason = "stale element reference"
                last_state = {"error": "element became stale"}
                time.sleep(poll)

            except NoSuchElementException:
                last_failure_reason = "element removed from DOM"
                last_state = {"error": "element no longer in DOM"}
                time.sleep(poll)

        # Timed out — capture final state for error message
        try:
            last_state = _capture_element_state(driver, element)
        except Exception:
            pass

        last_state["failure_reason"] = last_failure_reason

        raise WaitTimeoutError(
            condition=f"element ready ({last_failure_reason})",
            timeout=timeout,
            element_state=last_state,
        )

    @staticmethod
    def wait_for_element(
        driver: WebDriver,
        element: WebElement,
        timeout: float | None = None,
    ) -> WebElement:
        """Simplified wait — backwards compatible with Phase 1 API.

        Called by the action pipeline. Delegates to wait_for_element_ready.
        """
        return WaitEngine.wait_for_element_ready(driver, element, timeout=timeout)

    @staticmethod
    def wait_for_condition(
        condition: Callable[[], bool],
        description: str = "custom condition",
        timeout: float | None = None,
    ) -> bool:
        """Wait for a custom boolean condition to become True.

        Args:
            condition: A callable that returns True when satisfied.
            description: Human-readable description for error messages.
            timeout: Max wait time in seconds.

        Returns:
            True when the condition is met.

        Raises:
            WaitTimeoutError: If not met within timeout.
        """
        config = get_config()
        timeout = timeout or config.waits.default_element_timeout
        poll = config.waits.polling_interval
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                if condition():
                    return True
            except Exception:
                pass
            time.sleep(poll)

        raise WaitTimeoutError(condition=description, timeout=timeout)

    @staticmethod
    def wait_for_page_load(
        driver: WebDriver,
        timeout: float | None = None,
    ) -> None:
        """Wait for page to finish loading (document.readyState == 'complete').

        Args:
            driver: The WebDriver instance.
            timeout: Max wait time in seconds.

        Raises:
            WaitTimeoutError: If page doesn't load within timeout.
        """
        config = get_config()
        timeout = timeout or config.waits.navigation_timeout

        def page_ready() -> bool:
            try:
                state = driver.execute_script("return document.readyState")
                return state == "complete"
            except WebDriverException:
                return False

        WaitEngine.wait_for_condition(
            condition=page_ready,
            description="document.readyState == 'complete'",
            timeout=timeout,
        )

    @staticmethod
    def wait_for_network_idle(
        driver: WebDriver,
        idle_time: float | None = None,
        timeout: float | None = None,
    ) -> None:
        """Wait for network activity to settle (no pending XHR/fetch requests).

        Injects a JavaScript observer that tracks active XMLHttpRequest and
        fetch calls. Waits until no requests have been active for ``idle_time``
        seconds.

        Args:
            driver: The WebDriver instance.
            idle_time: Seconds of network quiet to consider "idle".
            timeout: Max wait time in seconds.

        Raises:
            WaitTimeoutError: If network doesn't idle within timeout.
        """
        config = get_config()
        idle_time = idle_time or config.waits.network_idle_timeout
        timeout = timeout or config.waits.navigation_timeout

        # Inject network observer
        try:
            driver.execute_script("""
                if (window.__pyshaft_network_observer) return;

                window.__pyshaft_active_requests = 0;
                window.__pyshaft_last_activity = Date.now();
                window.__pyshaft_network_observer = true;

                // Intercept XMLHttpRequest
                var origOpen = XMLHttpRequest.prototype.open;
                var origSend = XMLHttpRequest.prototype.send;

                XMLHttpRequest.prototype.open = function() {
                    this.__pyshaft_tracked = true;
                    return origOpen.apply(this, arguments);
                };

                XMLHttpRequest.prototype.send = function() {
                    if (this.__pyshaft_tracked) {
                        window.__pyshaft_active_requests++;
                        window.__pyshaft_last_activity = Date.now();

                        this.addEventListener('loadend', function() {
                            window.__pyshaft_active_requests =
                                Math.max(0, window.__pyshaft_active_requests - 1);
                            window.__pyshaft_last_activity = Date.now();
                        });
                    }
                    return origSend.apply(this, arguments);
                };

                // Intercept fetch
                var origFetch = window.fetch;
                window.fetch = function() {
                    window.__pyshaft_active_requests++;
                    window.__pyshaft_last_activity = Date.now();

                    return origFetch.apply(this, arguments).then(function(response) {
                        window.__pyshaft_active_requests =
                            Math.max(0, window.__pyshaft_active_requests - 1);
                        window.__pyshaft_last_activity = Date.now();
                        return response;
                    }).catch(function(error) {
                        window.__pyshaft_active_requests =
                            Math.max(0, window.__pyshaft_active_requests - 1);
                        window.__pyshaft_last_activity = Date.now();
                        throw error;
                    });
                };
            """)
        except Exception as e:
            logger.debug("Network observer injection failed: %s — skipping network idle wait", e)
            return

        idle_ms = idle_time * 1000

        def network_idle() -> bool:
            try:
                result = driver.execute_script("""
                    var active = window.__pyshaft_active_requests || 0;
                    var lastActivity = window.__pyshaft_last_activity || 0;
                    var elapsed = Date.now() - lastActivity;
                    return {active: active, elapsed: elapsed};
                """)
                if not result:
                    return True
                return result["active"] == 0 and result["elapsed"] >= idle_ms
            except Exception:
                return True  # Assume idle if we can't check

        WaitEngine.wait_for_condition(
            condition=network_idle,
            description=f"network idle for {idle_time}s",
            timeout=timeout,
        )

    @staticmethod
    def wait_for_dom_stable(
        driver: WebDriver,
        stability_time: float = 0.5,
        timeout: float | None = None,
    ) -> None:
        """Wait for the DOM to stop changing (no mutations for stability_time).

        Uses MutationObserver to detect DOM changes.

        Args:
            driver: The WebDriver instance.
            stability_time: Seconds of no DOM mutations to consider stable.
            timeout: Max wait time in seconds.
        """
        config = get_config()
        timeout = timeout or config.waits.default_element_timeout

        # Inject mutation observer
        try:
            driver.execute_script("""
                if (window.__pyshaft_mutation_observer) {
                    window.__pyshaft_mutation_observer.disconnect();
                }
                window.__pyshaft_last_mutation = Date.now();
                window.__pyshaft_mutation_observer = new MutationObserver(function() {
                    window.__pyshaft_last_mutation = Date.now();
                });
                window.__pyshaft_mutation_observer.observe(document.body, {
                    childList: true, subtree: true, attributes: true
                });
            """)
        except Exception as e:
            logger.debug("MutationObserver injection failed: %s", e)
            return

        stability_ms = stability_time * 1000

        def dom_stable() -> bool:
            try:
                elapsed = driver.execute_script(
                    "return Date.now() - (window.__pyshaft_last_mutation || 0);"
                )
                return elapsed >= stability_ms
            except Exception:
                return True

        try:
            WaitEngine.wait_for_condition(
                condition=dom_stable,
                description=f"DOM stable for {stability_time}s",
                timeout=timeout,
            )
        finally:
            # Cleanup observer
            try:
                driver.execute_script("""
                    if (window.__pyshaft_mutation_observer) {
                        window.__pyshaft_mutation_observer.disconnect();
                        window.__pyshaft_mutation_observer = null;
                    }
                """)
            except Exception:
                pass
