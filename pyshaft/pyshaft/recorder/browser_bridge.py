"""PyShaft Recorder — Browser Bridge.

Manages Chrome/Edge launch with CDP (Chrome DevTools Protocol),
injects recording/inspector JS, and relays DOM events to the GUI.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger("pyshaft.recorder.browser_bridge")

# Path to bundled JS scripts
_JS_DIR = Path(__file__).parent / "js"


class BrowserBridge:
    """Manages connection to Chrome via CDP for recording and inspection.

    Launches Chrome with --remote-debugging-port, connects via websocket,
    and injects JavaScript for event capture and element inspection.
    """

    def __init__(
        self,
        on_event: Callable[[dict], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
        port: int = 9222,
    ):
        self._on_event = on_event
        self._on_navigate = on_navigate
        self._port = port
        self._process: subprocess.Popen | None = None
        self._ws = None
        self._ws_thread: threading.Thread | None = None
        self._recording = False
        self._inspecting = False
        self._running = False
        self._msg_id = 0
        self._user_data_dir: str | None = None

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def launch(self, url: str = "about:blank", browser: str = "chrome") -> bool:
        """Launch Chrome with remote debugging enabled.

        Args:
            url: Initial URL to open.
            browser: Browser to use (chrome or edge).

        Returns:
            True if launch was successful.
        """
        chrome_paths = self._find_browser_paths(browser)
        if not chrome_paths:
            logger.error("No %s installation found", browser)
            return False

        # Create a temp user data dir to avoid conflicts with existing sessions
        self._user_data_dir = tempfile.mkdtemp(prefix="pyshaft_recorder_")

        chrome_path = chrome_paths[0]
        args = [
            chrome_path,
            f"--remote-debugging-port={self._port}",
            f"--user-data-dir={self._user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-infobars",
            "--disable-extensions",
            url,
        ]

        try:
            self._process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Chrome launched (PID=%d, port=%d)", self._process.pid, self._port)

            # Wait for CDP to be ready
            time.sleep(2)
            self._connect_cdp()
            return True

        except FileNotFoundError:
            logger.error("Chrome executable not found at %s", chrome_path)
            return False
        except Exception as e:
            logger.error("Failed to launch Chrome: %s", e)
            return False

    def close(self):
        """Close the browser and clean up."""
        self._running = False
        self._recording = False
        self._inspecting = False

        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

        # Clean up temp dir
        if self._user_data_dir:
            import shutil
            try:
                shutil.rmtree(self._user_data_dir, ignore_errors=True)
            except Exception:
                pass

        logger.info("Browser bridge closed")

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    # -------------------------------------------------------------------------
    # CDP Connection
    # -------------------------------------------------------------------------

    def _connect_cdp(self):
        """Connect to Chrome's CDP websocket."""
        try:
            import websocket
            import urllib.request

            # Get the websocket URL from the CDP endpoint
            url = f"http://localhost:{self._port}/json"
            for attempt in range(10):  # Retry up to 10 times
                try:
                    with urllib.request.urlopen(url, timeout=2) as resp:
                        tabs = json.loads(resp.read())
                        break
                except Exception:
                    time.sleep(0.5)
            else:
                logger.error("Could not connect to CDP endpoint after retries")
                return

            # Find the first page tab
            ws_url = None
            for tab in tabs:
                if tab.get("type") == "page":
                    ws_url = tab.get("webSocketDebuggerUrl")
                    break

            if not ws_url:
                logger.error("No page tab found in CDP")
                return

            # Connect websocket
            self._ws = websocket.WebSocket()
            self._ws.connect(ws_url)
            self._running = True

            # Enable necessary CDP domains
            self._send_cdp("Runtime.enable")
            self._send_cdp("Page.enable")
            self._send_cdp("DOM.enable")

            # Listen for console messages (our JS sends events via console.log)
            self._send_cdp("Runtime.enable")

            # Start message listener thread
            self._ws_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._ws_thread.start()

            logger.info("CDP connected via %s", ws_url)

        except ImportError:
            logger.warning("websocket-client not installed. Install with: pip install websocket-client")
        except Exception as e:
            logger.error("CDP connection failed: %s", e)

    def _send_cdp(self, method: str, params: dict | None = None) -> int:
        """Send a CDP command and return the message ID."""
        if not self._ws:
            return -1

        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method}
        if params:
            msg["params"] = params

        try:
            self._ws.send(json.dumps(msg))
        except Exception as e:
            logger.debug("CDP send failed: %s", e)

        return self._msg_id

    def _listen_loop(self):
        """Background thread that listens for CDP messages."""
        while self._running and self._ws:
            try:
                raw = self._ws.recv()
                if not raw:
                    continue

                msg = json.loads(raw)
                self._handle_cdp_message(msg)

            except Exception as e:
                if self._running:
                    logger.debug("CDP listen error: %s", e)
                break

    def _handle_cdp_message(self, msg: dict):
        """Process an incoming CDP message."""
        method = msg.get("method", "")

        # Console messages from our injected JS
        if method == "Runtime.consoleAPICalled":
            args = msg.get("params", {}).get("args", [])
            for arg in args:
                value = arg.get("value", "")
                if isinstance(value, str) and value.startswith("__PYSHAFT_EVENT__:"):
                    try:
                        event_data = json.loads(value[len("__PYSHAFT_EVENT__:"):])
                        if self._on_event:
                            self._on_event(event_data)
                    except json.JSONDecodeError:
                        pass

                elif isinstance(value, str) and value.startswith("__PYSHAFT_INSPECT__:"):
                    try:
                        inspect_data = json.loads(value[len("__PYSHAFT_INSPECT__:"):])
                        if self._on_event:
                            self._on_event({"type": "inspect", **inspect_data})
                    except json.JSONDecodeError:
                        pass

        # Page navigation
        elif method == "Page.navigatedWithinDocument" or method == "Page.frameNavigated":
            url = ""
            if method == "Page.navigatedWithinDocument":
                url = msg.get("params", {}).get("url", "")
            else:
                frame = msg.get("params", {}).get("frame", {})
                url = frame.get("url", "")

            if url and self._on_navigate:
                self._on_navigate(url)

            # Re-inject scripts after navigation
            if self._recording:
                time.sleep(0.5)  # Wait for page to load
                self._inject_recorder_js()
            if self._inspecting:
                time.sleep(0.5)
                self._inject_inspector_js()

    # -------------------------------------------------------------------------
    # Recording
    # -------------------------------------------------------------------------

    def start_recording(self):
        """Start recording user interactions."""
        self._recording = True
        self._inject_recorder_js()
        logger.info("Recording started")

    def stop_recording(self):
        """Stop recording."""
        self._recording = False
        # Remove recorder overlay
        self._evaluate_js("if(window.__pyshaft_recorder) window.__pyshaft_recorder.stop();")
        logger.info("Recording stopped")

    def pause_recording(self):
        """Pause recording (stop capturing events but keep JS injected)."""
        self._evaluate_js("if(window.__pyshaft_recorder) window.__pyshaft_recorder.pause();")

    def resume_recording(self):
        """Resume recording after pause."""
        self._evaluate_js("if(window.__pyshaft_recorder) window.__pyshaft_recorder.resume();")

    # -------------------------------------------------------------------------
    # Inspection
    # -------------------------------------------------------------------------

    def start_inspecting(self):
        """Start element inspection mode."""
        self._inspecting = True
        self._inject_inspector_js()
        logger.info("Inspector started")

    def stop_inspecting(self):
        """Stop inspection mode."""
        self._inspecting = False
        self._evaluate_js("if(window.__pyshaft_inspector) window.__pyshaft_inspector.stop();")
        logger.info("Inspector stopped")

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def navigate(self, url: str):
        """Navigate the browser to a URL."""
        self._send_cdp("Page.navigate", {"url": url})

    def get_current_url(self) -> str:
        """Get the current page URL via CDP."""
        # This is async in nature; for simplicity we use JS
        result = self._evaluate_js_sync("window.location.href")
        return result or ""

    # -------------------------------------------------------------------------
    # JS Injection
    # -------------------------------------------------------------------------

    def _inject_recorder_js(self):
        """Inject the recorder JavaScript into the page."""
        js_path = _JS_DIR / "recorder.js"
        if js_path.exists():
            js_code = js_path.read_text(encoding="utf-8")
            self._evaluate_js(js_code)
            logger.debug("Recorder JS injected")
        else:
            logger.warning("recorder.js not found at %s", js_path)

    def _inject_inspector_js(self):
        """Inject the inspector JavaScript into the page."""
        js_path = _JS_DIR / "inspector.js"
        if js_path.exists():
            js_code = js_path.read_text(encoding="utf-8")
            self._evaluate_js(js_code)
            logger.debug("Inspector JS injected")
        else:
            logger.warning("inspector.js not found at %s", js_path)

    def _evaluate_js(self, expression: str):
        """Evaluate JavaScript in the browser page."""
        self._send_cdp("Runtime.evaluate", {
            "expression": expression,
            "awaitPromise": False,
        })

    def _evaluate_js_sync(self, expression: str) -> str | None:
        """Evaluate JS and attempt to get the result (best-effort sync)."""
        # For true sync we'd need to wait for the response, but for simplicity
        # we just fire and forget. The caller should use callbacks for async results.
        self._evaluate_js(expression)
        return None

    # -------------------------------------------------------------------------
    # Browser Discovery
    # -------------------------------------------------------------------------

    @staticmethod
    def _find_browser_paths(browser: str = "chrome") -> list[str]:
        """Find Chrome/Edge executable paths on Windows."""
        paths = []

        if browser == "chrome":
            candidates = [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            ]
        elif browser == "edge":
            candidates = [
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            ]
        else:
            return []

        for path in candidates:
            if os.path.isfile(path):
                paths.append(path)

        return paths
