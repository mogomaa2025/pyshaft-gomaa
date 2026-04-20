"""PyShaft Report — Browser video recording via CDP screencast.

Records browser sessions as video using Chrome DevTools Protocol.
Falls back to a no-op when CDP is unavailable (Firefox) or ffmpeg is missing.
"""

from __future__ import annotations

import base64
import io
import logging
import threading
import time
from pathlib import Path
from typing import Any

from pyshaft.session import session_context

logger = logging.getLogger("pyshaft.report.video_recorder")


class VideoRecorder:
    """Records browser session as video using CDP screencast.

    Usage::

        recorder = VideoRecorder()
        recorder.start(driver, "output/video")
        # ... test actions ...
        video_path = recorder.stop()
    """

    def __init__(self) -> None:
        self._frames: list[bytes] = []
        self._recording = False
        self._output_path: Path | None = None
        self._thread: threading.Thread | None = None
        self._driver: Any = None
        self._fps = 4  # Frames per second for screencast

    def start(self, driver: Any, output_dir: str | Path) -> None:
        """Start recording the browser session.

        Args:
            driver: Selenium WebDriver instance.
            output_dir: Directory to save the video file.
        """
        self._driver = driver
        self._frames = []
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self._output_path = output_dir / f"recording_{int(time.time())}.webm"

        # Try CDP screencast (Chrome/Edge only)
        try:
            driver.execute_cdp_cmd("Page.startScreencast", {
                "format": "png",
                "quality": 50,
                "maxWidth": 1280,
                "maxHeight": 720,
                "everyNthFrame": 1,
            })
            self._recording = True
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            logger.info("Video recording started (CDP screencast)")
        except Exception as e:
            logger.warning("CDP screencast unavailable: %s. Video recording disabled.", e)
            self._recording = False

    def _capture_loop(self) -> None:
        """Background loop to capture screencast frames."""
        interval = 1.0 / self._fps
        while self._recording:
            try:
                # Poll for screencast frames via CDP
                result = self._driver.execute_cdp_cmd(
                    "Page.getScreencastFrame", {}
                )
                if result and "data" in result:
                    frame_data = base64.b64decode(result["data"])
                    self._frames.append(frame_data)
                    # Acknowledge the frame
                    self._driver.execute_cdp_cmd(
                        "Page.screencastFrameAck",
                        {"sessionId": result.get("sessionId", 0)},
                    )
            except Exception:
                # CDP screencast might not return frames continuously
                pass
            time.sleep(interval)

    def stop(self) -> str | None:
        """Stop recording and assemble frames into a video.

        Returns:
            Path to the video file, or None if recording failed.
        """
        if not self._recording:
            return None

        self._recording = False
        if self._thread:
            self._thread.join(timeout=5)

        # Stop CDP screencast
        try:
            self._driver.execute_cdp_cmd("Page.stopScreencast", {})
        except Exception:
            pass

        if not self._frames:
            logger.warning("No frames captured during recording")
            return None

        # Assemble frames into video using ffmpeg
        video_path = self._assemble_video()
        return video_path

    def _assemble_video(self) -> str | None:
        """Assemble captured PNG frames into a video file using ffmpeg."""
        try:
            import ffmpeg
        except ImportError:
            logger.warning(
                "ffmpeg-python not installed. Saving frames as individual PNGs. "
                "Install with: pip install pyshaft[video]"
            )
            return self._save_frames_fallback()

        if not self._output_path:
            return None

        # Write frames to temporary directory
        frames_dir = self._output_path.parent / "frames"
        frames_dir.mkdir(exist_ok=True)

        for i, frame in enumerate(self._frames):
            frame_path = frames_dir / f"frame_{i:05d}.png"
            frame_path.write_bytes(frame)

        # Use ffmpeg to assemble
        try:
            pattern = str(frames_dir / "frame_%05d.png")
            (
                ffmpeg
                .input(pattern, framerate=self._fps)
                .output(str(self._output_path), vcodec="libvpx-vp9", crf=30)
                .overwrite_output()
                .run(quiet=True)
            )
            logger.info("Video saved: %s", self._output_path)

            # Cleanup frames
            import shutil
            shutil.rmtree(frames_dir, ignore_errors=True)

            return str(self._output_path)
        except Exception as e:
            logger.error("Failed to assemble video: %s", e)
            return self._save_frames_fallback()

    def _save_frames_fallback(self) -> str | None:
        """Fallback: save frames as individual PNGs when ffmpeg is unavailable."""
        if not self._output_path:
            return None

        frames_dir = self._output_path.parent / "frames"
        frames_dir.mkdir(exist_ok=True)

        for i, frame in enumerate(self._frames):
            path = frames_dir / f"frame_{i:05d}.png"
            path.write_bytes(frame)

        logger.info("Saved %d frames to %s", len(self._frames), frames_dir)
        return str(frames_dir)

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def frame_count(self) -> int:
        return len(self._frames)
