"""PyShaft CLI — command-line interface.

Provides `pyshaft run`, `pyshaft inspect`, `pyshaft record`,
`pyshaft inspectapi`, and `pyshaft report serve` commands.
"""

from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> None:
    """PyShaft CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="pyshaft",
        description="PyShaft — Python test automation framework",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # pyshaft run
    run_parser = subparsers.add_parser("run", help="Run tests with PyShaft config")
    run_parser.add_argument("--demo", action="store_true", help="Enable demo mode")
    run_parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    run_parser.add_argument("--browser", type=str, help="Browser override (chrome/firefox/edge)")
    run_parser.add_argument("--env", type=str, default="dev", help="Environment (dev/staging/prod)")
    run_parser.add_argument("--tags", "-t", type=str, help="Run tests with specific tags (e.g., 'smoke', 'api')")
    run_parser.add_argument("--exclude-tags", type=str, help="Exclude tests with specific tags")
    run_parser.add_argument("--parallel", "-n", type=str, help="Number of parallel workers (auto or number)")
    run_parser.add_argument("--rerun", "-r", type=int, default=0, help="Number of retry attempts on failure")
    run_parser.add_argument("args", nargs="*", help="Additional pytest arguments")

    # pyshaft run-all (run all tests in a suite)
    run_all_parser = subparsers.add_parser("run-all", help="Run all tests with default configuration")
    run_all_parser.add_argument("--env", type=str, default="dev", help="Environment (dev/staging/prod)")
    run_all_parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    run_all_parser.add_argument("--report", action="store_true", help="Generate HTML report after run")
    run_all_parser.add_argument("args", nargs="*", help="Additional pytest arguments")

    # pyshaft run-suite (run specific test suite)
    suite_parser = subparsers.add_parser("run-suite", help="Run a specific test suite")
    suite_parser.add_argument("suite", type=str, help="Suite name (api/web/integration)")
    suite_parser.add_argument("--env", type=str, default="dev", help="Environment")
    suite_parser.add_argument("--tags", "-t", type=str, help="Filter by tags")

    # pyshaft inspect
    inspect_parser = subparsers.add_parser(
        "inspect", help="Launch the inspector GUI (browse & build test steps visually)",
    )
    inspect_parser.add_argument("--url", "-u", type=str, default=None, help="Start URL")
    inspect_parser.add_argument(
        "--browser", "-b", type=str, default="chrome",
        choices=["chrome", "edge"], help="Browser to use (default: chrome)",
    )

    # pyshaft record
    record_parser = subparsers.add_parser("record", help="Launch the recorder GUI (auto-capture mode)")
    record_parser.add_argument("--url", "-u", type=str, default=None, help="Start URL")
    record_parser.add_argument(
        "--browser", "-b", type=str, default="chrome",
        choices=["chrome", "edge"], help="Browser to use (default: chrome)",
    )

    # pyshaft inspectapi
    subparsers.add_parser(
        "inspectapi", help="Launch the API Inspector GUI (build & test API workflows visually)",
    )

    # pyshaft report serve
    report_parser = subparsers.add_parser("report", help="Report commands")
    report_subparsers = report_parser.add_subparsers(dest="report_command")
    serve_parser = report_subparsers.add_parser("serve", help="Start Flask dashboard server")
    serve_parser.add_argument(
        "--port", "-p", type=int, default=5000, help="Port to serve on (default: 5000)",
    )
    serve_parser.add_argument(
        "--dir", "-d", type=str, default="pyshaft-report",
        help="Report data directory (default: pyshaft-report)",
    )

    args = parser.parse_args()

    match args.command:
        case "run":
            _run_tests(args)
        case "run-all":
            _run_all_tests(args)
        case "run-suite":
            _run_suite(args)
        case "inspect":
            _launch_recorder(args, mode="inspect")
        case "record":
            _launch_recorder(args, mode="record")
        case "inspectapi":
            _launch_api_inspector()
        case "report":
            if args.report_command == "serve":
                _serve_report(port=args.port, report_dir=args.dir)
            else:
                report_parser.print_help()
        case _:
            parser.print_help()


def _run_tests(args: argparse.Namespace) -> None:
    """Run pytest with PyShaft configuration."""
    import os

    cmd = [sys.executable, "-m", "pytest"]

    # Set environment
    os.environ["PYSHAFT_ENV"] = args.env if hasattr(args, 'env') else "dev"

    if args.headless:
        os.environ["PYSHAFT_HEADLESS"] = "true"

    if args.browser:
        os.environ["PYSHAFT_BROWSER"] = args.browser

    # Tag filtering
    if hasattr(args, 'tags') and args.tags:
        cmd.extend(["-m", args.tags])
    if hasattr(args, 'exclude_tags') and args.exclude_tags:
        cmd.extend(["-m", f"not {args.exclude_tags}"])

    # Parallel execution
    if hasattr(args, 'parallel') and args.parallel:
        cmd.extend(["-n", args.parallel])

    # Retry attempts
    if hasattr(args, 'rerun') and args.rerun > 0:
        cmd.extend(["--reruns", str(args.rerun)])

    # Pass through additional args
    if args.args:
        cmd.extend(args.args)

    print(f"PyShaft: Running tests with {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def _run_all_tests(args: argparse.Namespace) -> None:
    """Run all tests with default configuration."""
    import os
    from pathlib import Path

    cmd = [sys.executable, "-m", "pytest"]

    # Set environment
    os.environ["PYSHAFT_ENV"] = args.env
    if args.headless:
        os.environ["PYSHAFT_HEADLESS"] = "true"

    # Auto-discover test paths
    test_paths = []
    for pattern in ["tests/", "tests/**/*.py"]:
        test_paths.extend(Path(".").glob(pattern))
    if test_paths:
        # Find unique test directories
        dirs = set(str(p.parent) for p in test_paths if p.suffix == ".py" and "test_" in p.name)
        cmd.extend(sorted(dirs)[:3])  # Add up to 3 test directories

    if args.report:
        cmd.extend(["--html=pyshaft-report/index.html", "--self-contained-html"])

    if args.args:
        cmd.extend(args.args)

    print(f"PyShaft: Running all tests...")
    print(f"  Environment: {args.env}")
    print(f"  Headless: {args.headless}")
    print(f"  Command: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def _run_suite(args: argparse.Namespace) -> None:
    """Run a specific test suite."""
    import os

    suite_map = {
        "api": "tests/unit/test_api*.py",
        "web": "tests/unit/test_*.py",
        "integration": "tests/integration/",
    }

    if args.suite not in suite_map:
        print(f"Unknown suite: {args.suite}")
        print(f"Available suites: {', '.join(suite_map.keys())}")
        sys.exit(1)

    cmd = [sys.executable, "-m", "pytest", suite_map[args.suite]]
    os.environ["PYSHAFT_ENV"] = args.env

    if args.tags:
        cmd.extend(["-m", args.tags])

    print(f"PyShaft: Running {args.suite} suite...")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def _launch_recorder(args: argparse.Namespace, mode: str = "inspect") -> None:
    """Launch the PyShaft Recorder GUI.

    Args:
        args: Parsed CLI arguments.
        mode: 'inspect' for inspector-first, 'record' for auto-capture.
    """
    try:
        from pyshaft.recorder.app import run_app
        run_app(url=args.url, mode=mode)
    except ImportError as e:
        if "PyQt6" in str(e):
            print(f"Error: {e}")
            print("PyShaft Recorder requires PyQt6 and PyQt6-WebEngine.")
            print("Install with: pip install pyshaft[recorder]")
        else:
            print(f"Failed to launch recorder: {e}")
            import traceback
            traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _launch_api_inspector() -> None:
    """Launch the PyShaft API Inspector GUI."""
    try:
        from pyshaft.recorder.api_inspector import run_api_app
        run_api_app()
    except ImportError as e:
        if "PyQt6" in str(e):
            print(f"Error: {e}")
            print("PyShaft API Inspector requires PyQt6.")
            print("Install with: pip install pyshaft[recorder]")
        else:
            print(f"Failed to launch API inspector: {e}")
            import traceback
            traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _serve_report(port: int = 5000, report_dir: str = "pyshaft-report") -> None:
    """Start the Flask dashboard server."""
    try:
        from pyshaft.report.flask_app import create_app
    except ImportError:
        print("Flask is required for the report dashboard.")
        print("Install with: pip install pyshaft[report]")
        sys.exit(1)

    import os
    from pathlib import Path

    report_path = Path(report_dir)
    if not report_path.exists():
        report_path.mkdir(parents=True, exist_ok=True)
        print(f"Created report directory: {report_path}")

    app = create_app(report_path)
    print(f"⚡ PyShaft Report Dashboard")
    print(f"  → http://localhost:{port}")
    print(f"  → Report dir: {report_path.resolve()}")
    print(f"  Press Ctrl+C to stop.\n")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()

