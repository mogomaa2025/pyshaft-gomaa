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
    run_parser.add_argument("args", nargs="*", help="Additional pytest arguments")

    # pyshaft init
    init_parser = subparsers.add_parser("init", help="Initialize a PyShaft enterprise project structure")
    init_parser.add_argument("--dir", "-d", type=str, default=".", help="Directory to initialize in (default: current)")

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
        case "init":
            _init_project(args)
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

    if args.headless:
        os.environ["PYSHAFT_HEADLESS"] = "true"

    if args.browser:
        os.environ["PYSHAFT_BROWSER"] = args.browser

    # Pass through additional args
    if args.args:
        cmd.extend(args.args)

    print(f"PyShaft: Running tests with {' '.join(cmd)}")
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


def _init_project(args: argparse.Namespace) -> None:
    """Initialize a PyShaft project structure."""
    from pathlib import Path
    
    base_dir = Path(args.dir).resolve()
    print(f"Initializing PyShaft Enterprise Project in {base_dir}")
    
    # 1. Create directories
    dirs = [
        "tests/api",
        "tests/web",
        "tests/data",
        "tests/pages",
        "reports",
        ".github/workflows",
    ]
    for d in dirs:
        path = base_dir / d
        path.mkdir(parents=True, exist_ok=True)
        # Add __init__.py to test dirs
        if d.startswith("tests/"):
            (path / "__init__.py").touch()
            
    # Create top level __init__.py
    (base_dir / "tests" / "__init__.py").touch()
    
    # 2. pytest.ini
    pytest_ini = base_dir / "pytest.ini"
    if not pytest_ini.exists():
        pytest_ini.write_text(
            "[pytest]\n"
            "testpaths = tests\n"
            "python_files = test_*.py\n"
            "markers =\n"
            "    pyshaft_api: mark test as API test\n"
            "    pyshaft_web: mark test as Web test\n"
            "addopts = -v --tb=short\n",
            encoding="utf-8"
        )
        
    # 3. conftest.py
    conftest = base_dir / "tests" / "conftest.py"
    if not conftest.exists():
        conftest.write_text(
            "import pytest\n"
            "from pyshaft.api import ApiClient\n\n"
            "@pytest.fixture(scope='session')\n"
            "def api():\n"
            "    \"\"\"Global API client fixture.\"\"\"\n"
            "    client = ApiClient()\n"
            "    yield client\n\n"
            "@pytest.fixture(scope='session')\n"
            "def test_data():\n"
            "    \"\"\"Load environment or global test data.\"\"\"\n"
            "    return {'env': 'qa'}\n",
            encoding="utf-8"
        )
        
    # 4. Sample API test
    sample_api = base_dir / "tests" / "api" / "test_sample_api.py"
    if not sample_api.exists():
        sample_api.write_text(
            "import pytest\n"
            "from pyshaft.api import ApiClient\n\n"
            "@pytest.mark.pyshaft_api\n"
            "def test_get_users(api: ApiClient):\n"
            "    api.request().get('https://jsonplaceholder.typicode.com/users').assert_status(200)\n",
            encoding="utf-8"
        )
        
    # 5. Sample Web test
    sample_web = base_dir / "tests" / "web" / "test_sample_web.py"
    if not sample_web.exists():
        sample_web.write_text(
            "import pytest\n"
            "from pyshaft import web as w\n\n"
            "@pytest.mark.pyshaft_web\n"
            "def test_search():\n"
            "    w.open_url('https://example.com')\n"
            "    w.assert_title('Example Domain')\n",
            encoding="utf-8"
        )

    print("Project initialized successfully!")
    print("   Run `pytest` to execute sample tests.")
    print("   Run `pyshaft inspectapi` to build API tests.")
    print("   Run `pyshaft inspect` to build Web tests.")


if __name__ == "__main__":
    main()
