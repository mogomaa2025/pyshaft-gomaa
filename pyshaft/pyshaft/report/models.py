"""PyShaft Report — Data models for report generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepRecord:
    """Single test step captured during execution."""

    action: str
    locator: str
    status: str  # "pass" or "fail"
    duration_ms: float
    timestamp: float
    screenshot: str | None = None
    error: str | None = None


@dataclass
class ScreenshotRecord:
    """Screenshot taken during test execution."""

    path: str
    label: str
    step_index: int | None = None
    timestamp: float = 0.0


@dataclass
class ApiCallRecord:
    """API call captured during test execution."""

    method: str
    url: str
    status_code: int
    duration_ms: float
    timestamp: float
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body: Any = None
    response_body: Any = None
    response_headers: dict[str, str] = field(default_factory=dict)


@dataclass
class TestResult:
    """Complete result of a single test."""

    name: str
    path: str
    status: str  # "passed", "failed", "skipped", "error"
    duration_ms: float
    started_at: float
    ended_at: float = 0.0
    steps: list[StepRecord] = field(default_factory=list)
    screenshots: list[ScreenshotRecord] = field(default_factory=list)
    video_path: str | None = None
    api_calls: list[ApiCallRecord] = field(default_factory=list)
    error: str | None = None
    error_traceback: str | None = None


@dataclass
class ReportData:
    """Aggregate report data for the entire test run."""

    suite_name: str = "PyShaft Test Suite"
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errored: int = 0
    duration_ms: float = 0.0
    started_at: float = 0.0
    ended_at: float = 0.0
    tests: list[TestResult] = field(default_factory=list)

    def compute_summary(self) -> None:
        """Recompute summary counts from test results."""
        self.total = len(self.tests)
        self.passed = sum(1 for t in self.tests if t.status == "passed")
        self.failed = sum(1 for t in self.tests if t.status == "failed")
        self.skipped = sum(1 for t in self.tests if t.status == "skipped")
        self.errored = sum(1 for t in self.tests if t.status == "error")
        if self.tests:
            self.started_at = min(t.started_at for t in self.tests)
            self.ended_at = max(t.ended_at for t in self.tests if t.ended_at)
            self.duration_ms = sum(t.duration_ms for t in self.tests)

    @property
    def pass_rate(self) -> float:
        """Pass rate as a percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100
