"""PyShaft pytest plugin — provides browser session fixtures and markers.

Registered as a pytest plugin via ``pyproject.toml`` entry point:
    [project.entry-points.pytest11]
    pyshaft = "pytest_pyshaft.plugin"
"""

from __future__ import annotations

import logging

import pytest

from pyshaft.config import ScopeType, get_config, load_config
from pyshaft.core.driver_factory import DriverFactory
from pyshaft.core.step_logger import step_logger
from pyshaft.session import session_context

logger = logging.getLogger("pytest_pyshaft.plugin")


# ---------------------------------------------------------------------------
# Configuration hook — runs before test collection
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register PyShaft CLI options."""
    parser.addoption(
        "--pyshaft-recorder",
        action="store_true",
        default=False,
        help="Launch the PyShaft Recorder GUI to record and generate test code.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register PyShaft markers and load configuration early."""
    config.addinivalue_line(
        "markers",
        "pyshaft_web: Opt-in to browser session for this test (opens a browser)",
    )
    config.addinivalue_line(
        "markers",
        "pyshaft_scope(scope): Override browser session scope for a test "
        "(session/module/function)",
    )

    # Test categorization markers
    config.addinivalue_line(
        "markers",
        "smoke: Quick smoke tests to verify basic functionality",
    )
    config.addinivalue_line(
        "markers",
        "regression: Full regression test suite",
    )
    config.addinivalue_line(
        "markers",
        "api: API test (no browser needed)",
    )
    config.addinivalue_line(
        "markers",
        "web: Web UI test (requires browser)",
    )
    config.addinivalue_line(
        "markers",
        "slow: Tests that take longer to run",
    )
    config.addinivalue_line(
        "markers",
        "integration: Integration tests spanning multiple services",
    )

    # Load pyshaft config at plugin init
    load_config()
    logger.info("PyShaft plugin configured")

    # Launch recorder GUI if --pyshaft-recorder flag is set
    if config.getoption("--pyshaft-recorder", default=False):
        _launch_recorder_gui()


def _launch_recorder_gui() -> None:
    """Launch the PyShaft Recorder GUI (blocks until closed)."""
    try:
        from pyshaft.recorder.app import run_app
        logger.info("Launching PyShaft Recorder GUI...")
        run_app()
    except ImportError:
        logger.error(
            "PyShaft Recorder requires PyQt6. Install with: pip install pyshaft[recorder]"
        )
        raise pytest.UsageError(
            "PyShaft Recorder requires PyQt6.\n"
            "Install with: pip install pyshaft[recorder]"
        )
    except SystemExit:
        # QApplication.exec() calls sys.exit() — catch it gracefully
        pass


# ---------------------------------------------------------------------------
# Core Browser Control — This logic decides if we should start a browser
# ---------------------------------------------------------------------------


def _should_start_browser(request: pytest.FixtureRequest) -> bool:
    """Check if the current test context requires a browser session."""
    # 1. Look for explicit markers
    if request.node.get_closest_marker("pyshaft_web"): return True
    if request.node.get_closest_marker("pyshaft_scope"): return True
    
    # 2. Look for fixture requests (direct or indirect)
    # Note: We ONLY check for "web". We do NOT check for "pyshaft_browser" 
    # because it is an autouse fixture and would always be present.
    if "web" in request.fixturenames: return True
    
    # 3. Check global config for auto-start
    config = get_config()
    # Note: We should probably add an 'auto_start' field to BrowserConfig if needed,
    # but for now we default to False.
    return getattr(config.browser, "auto_start", False)


# ---------------------------------------------------------------------------
# Scoped Fixtures — Only activate if _should_start_browser is True
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def _pyshaft_session_browser(request: pytest.FixtureRequest):
    """Session-scoped browser — shared across all tests."""
    # Note: We can't use _should_start_browser here easily because it's session-scoped.
    # We rely on the autouse fixture below to keep it alive if needed.
    config = get_config()
    if config.execution.scope != ScopeType.SESSION:
        yield None
        return

    driver = DriverFactory.create()
    session_context.start(driver, config.browser.browser)
    logger.info("Session-scoped browser started")

    yield driver

    session_context.close()
    logger.info("Session-scoped browser closed")


@pytest.fixture(scope="module")
def _pyshaft_module_browser(request: pytest.FixtureRequest):
    """Module-scoped browser — one per test file."""
    config = get_config()
    if config.execution.scope != ScopeType.MODULE:
        yield None
        return

    driver = DriverFactory.create()
    session_context.start(driver, config.browser.browser)
    logger.info("Module-scoped browser started")

    yield driver

    session_context.close()
    logger.info("Module-scoped browser closed")


@pytest.fixture(scope="function")
def _pyshaft_function_browser(request: pytest.FixtureRequest):
    """Function-scoped browser — fresh browser per test."""
    config = get_config()
    marker = request.node.get_closest_marker("pyshaft_scope")
    scope_override = marker.args[0] if marker else None

    needs_function = (
        config.execution.scope == ScopeType.FUNCTION or scope_override == ScopeType.FUNCTION
    )

    if not needs_function:
        yield None
        return

    driver = DriverFactory.create()
    session_context.start(driver, config.browser.browser)
    logger.info("Function-scoped browser started for %s", request.node.name)

    yield driver

    session_context.close()
    logger.info("Function-scoped browser closed for %s", request.node.name)


# ---------------------------------------------------------------------------
# User-facing Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def pyshaft_browser(request: pytest.FixtureRequest):
    """Auto-use fixture that manages browser lifecycle conditionally.
    
    If the test is an API test (no markers, no web fixture requested), 
    this fixture does nothing beyond resetting the logger.
    """
    step_logger.reset()

    # ── Report collector: start test ──────────────────────────────────────
    from pyshaft.report.collector import collector as _collector
    _collector.start_test(request.node.name, request.node.nodeid)
    step_logger.add_listener(_collector.add_step)
    
    if not _should_start_browser(request):
        yield
        _collector.end_test("passed")
        step_logger.remove_listener(_collector.add_step)
        return

    # Trigger the appropriate scoped fixture manually by requesting it
    scope = get_config().execution.scope
    marker = request.node.get_closest_marker("pyshaft_scope")
    if marker:
        scope = marker.args[0]

    if scope == ScopeType.SESSION:
        request.getfixturevalue("_pyshaft_session_browser")
    elif scope == ScopeType.MODULE:
        request.getfixturevalue("_pyshaft_module_browser")
    else:
        request.getfixturevalue("_pyshaft_function_browser")

    yield

    # Final flush: execute any pending action at the end of the test
    from pyshaft.web import web as w
    w.flush()

    # Remove listener after test
    step_logger.remove_listener(_collector.add_step)


@pytest.fixture
def web(pyshaft_browser):
    """Fixture alias to inject the web engine and ensure the browser is open."""
    from pyshaft.web import web as web_engine
    return web_engine

    # Post-test: step logger data is available for reporting


# ---------------------------------------------------------------------------
# Test lifecycle hooks
# ---------------------------------------------------------------------------


def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Capture test results, trigger screenshot on failure, and feed collector."""
    if call.when != "call":
        return

    config = get_config()
    from pyshaft.report.collector import collector as _collector

    if call.excinfo is not None:
        # Report failure to collector
        import traceback
        tb_str = "".join(traceback.format_exception(
            type(call.excinfo.value), call.excinfo.value, call.excinfo.tb
        ))
        _collector.end_test(
            "failed",
            error=str(call.excinfo.value),
            error_traceback=tb_str,
        )

        # Capture screenshot on test failure
        if config.report.screenshot_on_fail:
            try:
                if session_context.is_active:
                    from pyshaft.report.screenshot_capture import ScreenshotCapture
                    capture = ScreenshotCapture()
                    path = capture.capture_failure(item.name)
                    if path:
                        _collector.add_screenshot(item.name, path, "Failure")
            except Exception as e:
                logger.warning("Failed to capture screenshot: %s", e)
    else:
        _collector.end_test("passed")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Clean up all browser sessions and export reports at the end of the test run."""
    # Export reports
    config = get_config()
    from pyshaft.report.collector import collector as _collector
    from pyshaft.report.json_exporter import export_json
    from pyshaft.report.junit_writer import export_junit_xml
    from pathlib import Path

    report_dir = Path(config.report.output_dir)
    report_dir.mkdir(exist_ok=True, parents=True)
    report_data = _collector.get_report_data()
    has_failures = exitstatus != 0

    if report_data.tests:
        try:
            export_json(report_data, report_dir / "data.json")
            export_junit_xml(report_data, report_dir / "report.xml")
            
            # Generate HTML report
            try:
                from pyshaft.report.html_renderer import render_html
                html_path = render_html(report_data, report_dir)
                logger.info(f"HTML report generated: {html_path}")
                
                # Open report on failure if configured
                if config.report.open_on_fail and has_failures:
                    try:
                        import webbrowser
                        webbrowser.open(f"file://{html_path.absolute()}")
                        logger.info(f"Opened report: {html_path}")
                    except Exception as e:
                        logger.warning(f"Failed to open report: {e}")
            except Exception as e:
                logger.warning(f"Failed to generate HTML report: {e}")
            
            logger.info("Reports exported to %s", report_dir)
        except Exception as e:
            logger.warning("Failed to export reports: %s", e)

    session_context.close_all()
    logger.info("PyShaft session finished (exit=%d)", exitstatus)

