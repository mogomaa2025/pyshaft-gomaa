"""PyShaft Report — JUnit XML export for CI systems (Jenkins, GitHub Actions, GitLab)."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from pyshaft.report.models import ReportData

logger = logging.getLogger("pyshaft.report.junit_writer")


def export_junit_xml(data: ReportData, output_path: str | Path) -> Path:
    """Export report data as JUnit XML.

    Args:
        data: The complete report data.
        output_path: File path for the XML output.

    Returns:
        The resolved output path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    testsuites = ET.Element("testsuites")
    testsuites.set("name", data.suite_name)
    testsuites.set("tests", str(data.total))
    testsuites.set("failures", str(data.failed))
    testsuites.set("errors", str(data.errored))
    testsuites.set("skipped", str(data.skipped))
    testsuites.set("time", f"{data.duration_ms / 1000:.3f}")

    testsuite = ET.SubElement(testsuites, "testsuite")
    testsuite.set("name", data.suite_name)
    testsuite.set("tests", str(data.total))
    testsuite.set("failures", str(data.failed))
    testsuite.set("errors", str(data.errored))
    testsuite.set("skipped", str(data.skipped))
    testsuite.set("time", f"{data.duration_ms / 1000:.3f}")

    for test in data.tests:
        testcase = ET.SubElement(testsuite, "testcase")
        testcase.set("name", test.name)
        testcase.set("classname", test.path)
        testcase.set("time", f"{test.duration_ms / 1000:.3f}")

        if test.status == "failed":
            failure = ET.SubElement(testcase, "failure")
            failure.set("message", test.error or "Test failed")
            if test.error_traceback:
                failure.text = test.error_traceback

        elif test.status == "error":
            error = ET.SubElement(testcase, "error")
            error.set("message", test.error or "Test error")
            if test.error_traceback:
                error.text = test.error_traceback

        elif test.status == "skipped":
            skipped = ET.SubElement(testcase, "skipped")
            if test.error:
                skipped.set("message", test.error)

        # Add step output as system-out
        if test.steps:
            system_out = ET.SubElement(testcase, "system-out")
            step_lines = []
            for i, step in enumerate(test.steps):
                status_icon = "✓" if step.status == "pass" else "✗"
                step_lines.append(
                    f"  {status_icon} Step {i + 1}: {step.action}({step.locator}) "
                    f"[{step.duration_ms:.0f}ms]"
                )
                if step.error:
                    step_lines.append(f"    Error: {step.error}")
            system_out.text = "\n".join(step_lines)

    tree = ET.ElementTree(testsuites)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="unicode", xml_declaration=True)

    logger.info("JUnit XML exported: %s", output_path)
    return output_path
