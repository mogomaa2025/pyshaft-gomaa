"""PyShaft API Inspector — Self-contained HTML report generator.

Generates a single .html file with all CSS/JS inlined for offline viewing.
Used by run_collection/run_folder to produce test execution reports.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StepResult:
    """Result of a single API request execution."""
    name: str = ""
    method: str = "GET"
    url: str = ""
    status_code: int = 0
    expected_status: int = 200
    duration_ms: float = 0.0
    success: bool = True
    error: str = ""
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body: str = ""
    response_body: str = ""
    assertions: list[dict[str, Any]] = field(default_factory=list)
    extractions: list[dict[str, str]] = field(default_factory=list)


@dataclass
class RunReport:
    """Complete report for a collection/folder run."""
    name: str = "API Run"
    total: int = 0
    passed: int = 0
    failed: int = 0
    duration_ms: float = 0.0
    started_at: str = ""
    ended_at: str = ""
    environment: str = "Default"
    steps: list[StepResult] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)

    def compute(self) -> None:
        self.total = len(self.steps)
        self.passed = sum(1 for s in self.steps if s.success)
        self.failed = self.total - self.passed
        self.duration_ms = sum(s.duration_ms for s in self.steps)


def generate_run_report(report: RunReport, output_path: str | Path) -> Path:
    """Generate a self-contained HTML report file."""
    report.compute()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    pass_rate = (report.passed / report.total * 100) if report.total else 0
    steps_html = _build_steps(report.steps)
    summary_json = json.dumps({
        "labels": ["Passed", "Failed"],
        "data": [report.passed, report.failed],
        "colors": ["#3FB950", "#F85149"]
    })

    html = _TEMPLATE.format(
        title=report.name,
        total=report.total,
        passed=report.passed,
        failed=report.failed,
        pass_rate=f"{pass_rate:.1f}",
        duration=f"{report.duration_ms / 1000:.2f}",
        started=report.started_at,
        ended=report.ended_at,
        environment=report.environment,
        steps_html=steps_html,
        summary_json=summary_json,
    )

    path.write_text(html, encoding="utf-8")
    return path


def _build_steps(steps: list[StepResult]) -> str:
    rows = []
    for i, s in enumerate(steps):
        badge_cls = "passed" if s.success else "failed"
        status_text = f"{s.status_code}" if s.status_code else "ERR"
        dur = f"{s.duration_ms:.0f}ms"

        # Request body
        req_body_html = ""
        if s.request_body:
            try:
                formatted = json.dumps(json.loads(s.request_body), indent=2)
            except Exception:
                formatted = s.request_body
            req_body_html = f'<div class="body-section"><div class="body-label">Request Body</div><pre><code>{_esc(formatted)}</code></pre></div>'

        # Response body
        resp_body_html = ""
        if s.response_body:
            try:
                formatted = json.dumps(json.loads(s.response_body) if isinstance(s.response_body, str) else s.response_body, indent=2)
            except Exception:
                formatted = str(s.response_body)
            resp_body_html = f'<div class="body-section"><div class="body-label">Response Body</div><pre><code>{_esc(formatted)}</code></pre></div>'

        # Error
        error_html = f'<div class="step-error">{_esc(s.error)}</div>' if s.error else ""

        # Assertions
        assert_html = ""
        if s.assertions:
            assert_rows = ""
            for a in s.assertions:
                a_status = "✓" if a.get("passed", True) else "✗"
                a_cls = "assert-pass" if a.get("passed", True) else "assert-fail"
                assert_rows += f'<tr class="{a_cls}"><td>{a_status}</td><td>{_esc(a.get("type", ""))}</td><td><code>{_esc(a.get("path", ""))}</code></td><td>{_esc(str(a.get("expected", "")))}</td><td>{_esc(str(a.get("actual", "")))}</td></tr>'
            assert_html = f'<div class="body-section"><div class="body-label">Assertions</div><table class="assert-table"><tr><th></th><th>Type</th><th>Path</th><th>Expected</th><th>Actual</th></tr>{assert_rows}</table></div>'

        rows.append(f"""
        <div class="step-card {'step-pass' if s.success else 'step-fail'}" onclick="toggleDetail('detail-{i}')">
            <div class="step-header">
                <span class="step-num">{i + 1}</span>
                <span class="method-badge method-{s.method.lower()}">{s.method}</span>
                <span class="step-name">{_esc(s.name)}</span>
                <span class="step-spacer"></span>
                <span class="badge badge-{badge_cls}">{status_text}</span>
                <span class="step-dur">{dur}</span>
            </div>
            <div class="step-url">{_esc(s.url)}</div>
            <div id="detail-{i}" class="step-detail" style="display:none;">
                {error_html}{req_body_html}{resp_body_html}{assert_html}
            </div>
        </div>""")

    return "\n".join(rows)


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — PyShaft Report</title>
<style>
:root {{
    --bg: #0D1117; --bg2: #161B22; --bg3: #1C2333; --bg4: #242D3D;
    --border: #30363D; --text: #E6EDF3; --muted: #8B949E; --dim: #6E7681;
    --purple: #6C63FF; --green: #3FB950; --red: #F85149; --blue: #58A6FF;
    --orange: #F0883E; --yellow: #E3B341;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
.container {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
.header {{ text-align: center; padding: 40px 0 24px; }}
.header h1 {{ font-size: 28px; font-weight: 800; }}
.header h1 span {{ color: var(--purple); }}
.header .subtitle {{ color: var(--muted); font-size: 13px; margin-top: 4px; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 24px; }}
.stat {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 10px; padding: 16px; text-align: center; }}
.stat-label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--dim); }}
.stat-value {{ font-size: 28px; font-weight: 800; margin-top: 4px; }}
.stat-value.green {{ color: var(--green); }}
.stat-value.red {{ color: var(--red); }}
.stat-value.blue {{ color: var(--blue); }}
.progress {{ height: 6px; background: var(--bg3); border-radius: 3px; overflow: hidden; margin: 24px 0 8px; }}
.progress-fill {{ height: 100%; border-radius: 3px; transition: width 0.6s ease; }}
.pass-rate {{ text-align: center; color: var(--muted); font-size: 13px; margin-bottom: 24px; }}
.section-title {{ font-size: 15px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin: 28px 0 12px; display: flex; align-items: center; gap: 8px; }}
.step-card {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px; cursor: pointer; transition: border-color 0.2s; }}
.step-card:hover {{ border-color: var(--purple); }}
.step-pass {{ border-left: 3px solid var(--green); }}
.step-fail {{ border-left: 3px solid var(--red); }}
.step-header {{ display: flex; align-items: center; gap: 10px; padding: 12px 16px; }}
.step-num {{ color: var(--dim); font-size: 12px; font-weight: 700; min-width: 24px; }}
.step-name {{ font-weight: 600; font-size: 14px; }}
.step-spacer {{ flex: 1; }}
.step-dur {{ color: var(--muted); font-size: 12px; font-family: monospace; min-width: 60px; text-align: right; }}
.step-url {{ padding: 0 16px 10px 50px; font-family: monospace; font-size: 12px; color: var(--dim); word-break: break-all; }}
.method-badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; color: white; }}
.method-get {{ background: var(--green); }}
.method-post {{ background: var(--blue); }}
.method-put {{ background: var(--yellow); }}
.method-patch {{ background: var(--orange); }}
.method-delete {{ background: var(--red); }}
.method-head,.method-options {{ background: var(--dim); }}
.badge {{ padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }}
.badge-passed {{ background: rgba(63,185,80,0.15); color: var(--green); }}
.badge-failed {{ background: rgba(248,81,73,0.15); color: var(--red); }}
.step-detail {{ padding: 0 16px 16px 50px; }}
.step-error {{ background: rgba(248,81,73,0.1); border: 1px solid rgba(248,81,73,0.3); border-radius: 6px; padding: 10px 14px; color: var(--red); font-size: 13px; margin-bottom: 8px; }}
.body-section {{ margin-top: 10px; }}
.body-label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--dim); margin-bottom: 4px; }}
pre {{ background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; overflow-x: auto; font-size: 12px; font-family: 'Cascadia Code', monospace; max-height: 300px; overflow-y: auto; }}
.assert-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
.assert-table th {{ text-align: left; padding: 6px 10px; color: var(--dim); border-bottom: 1px solid var(--border); font-size: 10px; text-transform: uppercase; }}
.assert-table td {{ padding: 6px 10px; border-bottom: 1px solid var(--border); }}
.assert-pass td:first-child {{ color: var(--green); }}
.assert-fail td:first-child {{ color: var(--red); font-weight: 700; }}
.assert-fail {{ background: rgba(248,81,73,0.05); }}
.footer {{ text-align: center; padding: 32px 0; color: var(--dim); font-size: 12px; }}
.filters {{ display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }}
.filter-btn {{ padding: 5px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; border: 1px solid var(--border); background: var(--bg3); color: var(--muted); cursor: pointer; transition: all 0.2s; }}
.filter-btn:hover,.filter-btn.active {{ color: var(--text); border-color: var(--purple); background: rgba(108,99,255,0.15); }}
.waterfall {{ margin: 16px 0; }}
.wf-bar {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-size: 12px; }}
.wf-label {{ min-width: 180px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--muted); }}
.wf-track {{ flex: 1; height: 14px; background: var(--bg3); border-radius: 3px; overflow: hidden; }}
.wf-fill {{ height: 100%; border-radius: 3px; min-width: 2px; transition: width 0.4s ease; }}
.wf-dur {{ min-width: 60px; text-align: right; font-family: monospace; color: var(--dim); }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>⚡ <span>PyShaft</span> Report</h1>
        <div class="subtitle">{title} · {started} → {ended} · Environment: {environment}</div>
    </div>

    <div class="summary">
        <div class="stat"><div class="stat-label">Total</div><div class="stat-value">{total}</div></div>
        <div class="stat"><div class="stat-label">Passed</div><div class="stat-value green">{passed}</div></div>
        <div class="stat"><div class="stat-label">Failed</div><div class="stat-value red">{failed}</div></div>
        <div class="stat"><div class="stat-label">Duration</div><div class="stat-value blue">{duration}s</div></div>
    </div>

    <div class="progress"><div class="progress-fill" style="width: {pass_rate}%; background: linear-gradient(90deg, var(--green), var(--green));"></div></div>
    <div class="pass-rate">{pass_rate}% Pass Rate</div>

    <div class="section-title">📊 Timing Waterfall</div>
    <div class="waterfall" id="waterfall"></div>

    <div class="section-title">📋 Results</div>
    <div class="filters">
        <button class="filter-btn active" onclick="filterSteps('all', this)">All ({total})</button>
        <button class="filter-btn" onclick="filterSteps('pass', this)">✓ Passed ({passed})</button>
        <button class="filter-btn" onclick="filterSteps('fail', this)">✗ Failed ({failed})</button>
    </div>
    <div id="steps">{steps_html}</div>

    <div class="footer">Generated by ⚡ PyShaft API Inspector</div>
</div>
<script>
function toggleDetail(id) {{
    const el = document.getElementById(id);
    if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}}
function filterSteps(mode, btn) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.step-card').forEach(card => {{
        if (mode === 'all') card.style.display = '';
        else if (mode === 'pass') card.style.display = card.classList.contains('step-pass') ? '' : 'none';
        else card.style.display = card.classList.contains('step-fail') ? '' : 'none';
    }});
}}
// Waterfall chart
(function() {{
    const data = {summary_json};
    const cards = document.querySelectorAll('.step-card');
    const wf = document.getElementById('waterfall');
    let maxDur = 1;
    const durations = [];
    cards.forEach(c => {{
        const dur = parseFloat(c.querySelector('.step-dur')?.textContent) || 0;
        durations.push(dur);
        if (dur > maxDur) maxDur = dur;
    }});
    cards.forEach((c, i) => {{
        const name = c.querySelector('.step-name')?.textContent || '';
        const dur = durations[i];
        const pct = (dur / maxDur * 100).toFixed(1);
        const pass = c.classList.contains('step-pass');
        const color = pass ? 'var(--green)' : 'var(--red)';
        wf.innerHTML += `<div class="wf-bar"><div class="wf-label">${{name}}</div><div class="wf-track"><div class="wf-fill" style="width:${{pct}}%;background:${{color}};"></div></div><div class="wf-dur">${{dur.toFixed(0)}}ms</div></div>`;
    }});
}})();
</script>
</body>
</html>"""
