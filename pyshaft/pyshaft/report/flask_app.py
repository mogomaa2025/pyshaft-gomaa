"""PyShaft Report — Flask dashboard application.

Serves an interactive test report dashboard with step timelines,
screenshots, video playback, API call tracking, and timing breakdown.

Usage::

    pyshaft report serve
    pyshaft report serve --port 5000
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pyshaft.report.json_exporter import load_json
from pyshaft.report.models import ReportData

logger = logging.getLogger("pyshaft.report.flask_app")


def create_app(report_dir: str | Path) -> Any:
    """Create the Flask dashboard application.

    Args:
        report_dir: Directory containing report data (data.json, screenshots/, videos/).

    Returns:
        Flask application instance.
    """
    try:
        from flask import Flask, render_template, send_from_directory, jsonify, abort
    except ImportError:
        raise ImportError(
            "Flask is required for the report dashboard.\n"
            "Install with: pip install pyshaft[report]"
        )

    report_dir = Path(report_dir)
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    def _load_report() -> ReportData:
        """Load report data from the data.json file."""
        data_file = report_dir / "data.json"
        if not data_file.exists():
            return ReportData()
        return load_json(data_file)

    @app.route("/")
    def dashboard():
        """Main dashboard page — summary cards, test list, timing chart."""
        data = _load_report()
        return render_template("dashboard.html", report=data)

    @app.route("/test/<int:test_index>")
    def test_detail(test_index: int):
        """Individual test detail — step timeline, screenshots, video, API calls."""
        data = _load_report()
        if test_index >= len(data.tests):
            abort(404)
        test = data.tests[test_index]
        return render_template("test_detail.html", test=test, test_index=test_index, report=data)

    @app.route("/api-calls")
    def api_calls():
        """All API calls across tests."""
        data = _load_report()
        all_calls = []
        for test in data.tests:
            for call in test.api_calls:
                all_calls.append({"test_name": test.name, **_call_to_dict(call)})
        return render_template("api_calls.html", calls=all_calls, report=data)

    @app.route("/screenshots/<path:filename>")
    def serve_screenshot(filename: str):
        """Serve screenshot images."""
        screenshots_dir = report_dir / "screenshots"
        return send_from_directory(str(screenshots_dir), filename)

    @app.route("/videos/<path:filename>")
    def serve_video(filename: str):
        """Serve video files."""
        videos_dir = report_dir / "videos"
        return send_from_directory(str(videos_dir), filename)

    @app.route("/report.json")
    def download_json():
        """Download raw JSON report."""
        data_file = report_dir / "data.json"
        if not data_file.exists():
            abort(404)
        return send_from_directory(str(report_dir), "data.json", mimetype="application/json")

    @app.route("/report.xml")
    def download_xml():
        """Download JUnit XML report."""
        xml_file = report_dir / "report.xml"
        if not xml_file.exists():
            abort(404)
        return send_from_directory(str(report_dir), "report.xml", mimetype="application/xml")

    @app.route("/api/report")
    def api_report():
        """API endpoint — return report data as JSON."""
        data = _load_report()
        from dataclasses import asdict
        return jsonify(asdict(data))

    return app


def _call_to_dict(call) -> dict:
    """Convert an ApiCallRecord to a serializable dict."""
    return {
        "method": call.method,
        "url": call.url,
        "status_code": call.status_code,
        "duration_ms": call.duration_ms,
        "timestamp": call.timestamp,
    }
