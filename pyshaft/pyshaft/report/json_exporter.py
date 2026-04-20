"""PyShaft Report — JSON export for CI integration."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from pyshaft.report.models import ReportData

logger = logging.getLogger("pyshaft.report.json_exporter")


def export_json(data: ReportData, output_path: str | Path) -> Path:
    """Export report data as a JSON file.

    Args:
        data: The complete report data.
        output_path: File path for the JSON output.

    Returns:
        The resolved output path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report_dict = asdict(data)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, default=str)

    logger.info("JSON report exported: %s", output_path)
    return output_path


def load_json(input_path: str | Path) -> ReportData:
    """Load report data from a JSON file.

    Args:
        input_path: Path to the JSON report file.

    Returns:
        ReportData populated from the JSON.
    """
    from pyshaft.report.models import (
        ApiCallRecord,
        ScreenshotRecord,
        StepRecord,
        TestResult,
    )

    input_path = Path(input_path)
    with open(input_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    tests = []
    for t in raw.get("tests", []):
        steps = [StepRecord(**s) for s in t.pop("steps", [])]
        screenshots = [ScreenshotRecord(**s) for s in t.pop("screenshots", [])]
        api_calls = [ApiCallRecord(**a) for a in t.pop("api_calls", [])]
        tests.append(TestResult(
            **t,
            steps=steps,
            screenshots=screenshots,
            api_calls=api_calls,
        ))

    raw.pop("tests", None)
    return ReportData(**raw, tests=tests)
