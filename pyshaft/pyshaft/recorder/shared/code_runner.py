import io
import contextlib
import textwrap
import threading
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from pyshaft.recorder.shared.console_dock import PyShaftConsole


class CodeRunner:
    """Helper class to run generated Python code directly or as pytest tests."""

    @staticmethod
    def run_directly(code: str, console: PyShaftConsole, on_success: Callable[[], None] = None, on_error: Callable[[Exception], None] = None) -> None:
        """Execute Python code directly in a background thread."""
        console.log("Running code directly...", "header")

        def _worker():
            # Dedent selected code to remove common leading whitespace
            clean_code = textwrap.dedent(code).strip()

            output = io.StringIO()
            try:
                # Provide useful imports in the exec namespace
                exec_globals = {"__name__": "__main__"}
                try:
                    import pyshaft.api as api
                    exec_globals["api"] = api
                except ImportError:
                    pass
                try:
                    import pyshaft.web as w
                    from pyshaft.locator import role, text, label, placeholder, testid, id_, cls, css_, xpath, tag, attr, any_
                    from pyshaft.web import button, textbox, input_, checkbox, radio, link, menu, menuitem, dialog, modal, form, heading, alert, spinner, image, listbox, option, combobox, password, email, submit
                    
                    exec_globals["w"] = w
                    # Inject locators
                    for item in [role, text, label, placeholder, testid, id_, cls, css_, xpath, tag, attr, any_]:
                        exec_globals[item.__name__] = item
                    # Inject elements
                    for item in [button, textbox, input_, checkbox, radio, link, menu, menuitem, dialog, modal, form, heading, alert, spinner, image, listbox, option, combobox, password, email, submit]:
                        if hasattr(item, "__name__"):
                            exec_globals[item.__name__] = item
                        else:
                            exec_globals[item] = item
                except ImportError:
                    pass
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    exec(clean_code, exec_globals)
                result = output.getvalue()
                if result:
                    for line in result.strip().split("\n"):
                        console.log(line, "info")
                console.log("Code execution completed.", "success")
                if on_success:
                    on_success()
            except Exception as e:
                result = output.getvalue()
                if result:
                    for line in result.strip().split("\n"):
                        console.log(line, "info")
                console.log(f"Error: {e}", "error")
                if on_error:
                    on_error(e)

        threading.Thread(target=_worker, daemon=True).start()

    @staticmethod
    def run_as_test(code: str, console: PyShaftConsole, on_success: Callable[[], None] = None, on_error: Callable[[Exception], None] = None) -> None:
        """Run generated code as a pytest test."""
        console.log("Running as pytest test...", "header")

        def _worker():
            clean_code = textwrap.dedent(code).strip()
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                test_file = temp_path / "test_generated.py"
                test_file.write_text(clean_code, encoding="utf-8")
                
                try:
                    process = subprocess.Popen(
                        [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                    
                    for line in iter(process.stdout.readline, ""):
                        line = line.strip()
                        if not line:
                            continue
                        if "PASSED" in line:
                            console.log(line, "success")
                        elif "FAILED" in line or "ERROR" in line:
                            console.log(line, "error")
                        else:
                            console.log(line, "info")
                            
                    process.wait()
                    if process.returncode == 0:
                        console.log("Test execution passed.", "success")
                        if on_success:
                            on_success()
                    else:
                        console.log(f"Test execution failed (exit code {process.returncode}).", "error")
                        if on_error:
                            on_error(Exception(f"pytest exited with code {process.returncode}"))
                            
                except Exception as e:
                    console.log(f"Failed to start pytest: {e}", "error")
                    if on_error:
                        on_error(e)

        threading.Thread(target=_worker, daemon=True).start()
