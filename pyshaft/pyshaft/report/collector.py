"""PyShaft Report — StepCollector singleton for capturing test execution data."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from pyshaft.core.step_logger import Step
from pyshaft.report.models import (
    ApiCallRecord,
    ReportData,
    ScreenshotRecord,
    StepRecord,
    TestResult,
)

logger = logging.getLogger("pyshaft.report.collector")


class StepCollector:
    """Collects execution data from every test during a pytest run.

    Singleton pattern — one instance per test session,
    reset per test via ``start_test`` / ``end_test``.
    """

    def __init__(self) -> None:
        self._report = ReportData()
        self._current_test: TestResult | None = None
        self._test_start_time: float = 0.0

    # ── Test lifecycle ────────────────────────────────────────────────────

    def start_test(self, test_name: str, test_path: str) -> None:
        """Signal that a new test is starting."""
        self._test_start_time = time.time()
        self._current_test = TestResult(
            name=test_name,
            path=test_path,
            status="running",
            duration_ms=0.0,
            started_at=self._test_start_time,
        )
        logger.debug("Collector: started test %s", test_name)

    def end_test(
        self,
        status: str,
        duration_ms: float | None = None,
        error: str | None = None,
        error_traceback: str | None = None,
    ) -> None:
        """Signal that the current test has finished."""
        if not self._current_test:
            return

        self._current_test.status = status
        self._current_test.ended_at = time.time()
        self._current_test.duration_ms = duration_ms or (
            (self._current_test.ended_at - self._test_start_time) * 1000
        )
        self._current_test.error = error
        self._current_test.error_traceback = error_traceback

        self._report.tests.append(self._current_test)
        logger.debug(
            "Collector: ended test %s [%s] %.1fms",
            self._current_test.name,
            status,
            self._current_test.duration_ms,
        )
        self._current_test = None

    # ── Step-level data ───────────────────────────────────────────────────

    def add_step(self, step: Step) -> None:
        """Record a step from StepLogger."""
        if not self._current_test:
            return

        record = StepRecord(
            action=step.action,
            locator=step.locator,
            status=step.status,
            duration_ms=step.duration_ms,
            timestamp=step.timestamp,
            screenshot=step.screenshot,
            error=step.error,
        )
        self._current_test.steps.append(record)

    def add_screenshot(self, test_name: str, path: str, label: str = "") -> None:
        """Attach a screenshot to the current test."""
        if not self._current_test:
            return

        record = ScreenshotRecord(
            path=path,
            label=label or f"Step {len(self._current_test.screenshots) + 1}",
            step_index=len(self._current_test.steps) - 1 if self._current_test.steps else None,
            timestamp=time.time(),
        )
        self._current_test.screenshots.append(record)

    def add_video(self, test_name: str, path: str) -> None:
        """Attach a video recording to the current test."""
        if not self._current_test:
            return
        self._current_test.video_path = path

    def add_api_call(
        self,
        test_name: str,
        method: str,
        url: str,
        status_code: int,
        duration_ms: float,
        request_body: Any = None,
        response_body: Any = None,
        request_headers: dict[str, str] | None = None,
        response_headers: dict[str, str] | None = None,
    ) -> None:
        """Record an API call made during the current test."""
        if not self._current_test:
            return

        record = ApiCallRecord(
            method=method,
            url=url,
            status_code=status_code,
            duration_ms=duration_ms,
            timestamp=time.time(),
            request_headers=request_headers or {},
            request_body=request_body,
            response_body=response_body,
            response_headers=response_headers or {},
        )
        self._current_test.api_calls.append(record)

    # ── Report output ─────────────────────────────────────────────────────

    def get_report_data(self) -> ReportData:
        """Return finalized report data with computed summary."""
        self._report.compute_summary()
        return self._report

    def reset(self) -> None:
        """Reset collector for a fresh session."""
        self._report = ReportData()
        self._current_test = None


# Module-level singleton
collector = StepCollector()
