"""PyShaft configuration system — pyshaft.toml loader with sensible defaults.

Loads configuration from pyshaft.toml, merges with defaults, and supports
environment variable overrides (PYSHAFT_BROWSER, PYSHAFT_HEADLESS, etc.).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, fields
from enum import StrEnum
from pathlib import Path
from typing import Any

from pyshaft.exceptions import ConfigError

logger = logging.getLogger("pyshaft.config")

# ---------------------------------------------------------------------------
# Enums for constrained config values
# ---------------------------------------------------------------------------


class BrowserType(StrEnum):
    """Supported browser types."""
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"


class ScopeType(StrEnum):
    """Supported session scopes."""
    SESSION = "session"
    MODULE = "module"
    FUNCTION = "function"


# ---------------------------------------------------------------------------
# Config dataclasses — one per TOML section
# ---------------------------------------------------------------------------


@dataclass
class BrowserConfig:
    """[browser] section — browser choice, window, base URL."""
    browser: str = "chrome"
    headless: bool = False
    window_size: str = "1920x1080"
    base_url: str = ""
    navigation_timeout: int = 30


@dataclass
class ExecutionConfig:
    """[execution] section — parallel, retry, scope."""
    parallel: bool = False
    workers: str = "auto"
    retry_attempts: int = 0
    scope: str = "session"


@dataclass
class WaitsConfig:
    """[waits] section — auto-wait pipeline tuning."""
    default_element_timeout: float = 10.0
    polling_interval: float = 0.25
    stability_threshold: float = 0.3
    network_idle_timeout: float = 3.0
    navigation_timeout: float = 30.0
    respect_native_waits: bool = True


@dataclass
class ValidationsConfig:
    """[validations] section — enforcement guards."""
    force_element_visibility: bool = True
    force_locator_unique: bool = False
    force_text_verification: bool = False
    force_navigation_check: bool = True


@dataclass
class ActionsConfig:
    """[actions] section — action behavior toggles."""
    js_click_fallback: bool = True


@dataclass
class ReportConfig:
    """[report] section — output and capture settings."""
    output_dir: str = "pyshaft-report"
    downloads_dir: str = "pyshaft-downloads"
    screenshot_on_fail: bool = True
    screenshot_on_step: bool = False
    video_on_fail: bool = False
    junit_xml: bool = True
    json_report: bool = True
    open_on_fail: bool = False  # Open HTML report automatically on test failure


@dataclass
class ApiConfig:
    """[api] section — REST API testing defaults."""
    base_url: str = ""
    timeout: float = 30.0
    verify_ssl: bool = True


@dataclass
class Config:
    """Root configuration object — aggregates all sections."""
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    waits: WaitsConfig = field(default_factory=WaitsConfig)
    validations: ValidationsConfig = field(default_factory=ValidationsConfig)
    actions: ActionsConfig = field(default_factory=ActionsConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    api: ApiConfig = field(default_factory=ApiConfig)


# ---------------------------------------------------------------------------
# TOML section → dataclass mapping
# ---------------------------------------------------------------------------

_SECTION_MAP: dict[str, type] = {
    "browser": BrowserConfig,
    "execution": ExecutionConfig,
    "waits": WaitsConfig,
    "validations": ValidationsConfig,
    "actions": ActionsConfig,
    "report": ReportConfig,
    "api": ApiConfig,
}

# ---------------------------------------------------------------------------
# Singleton state
# ---------------------------------------------------------------------------

_config: Config | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_config(path: str | Path | None = None) -> Config:
    """Load configuration from pyshaft.toml, merge with defaults.

    Search order:
        1. Explicit path argument
        2. Current working directory
        3. Parent directories (up to root)

    Environment variables override file values:
        PYSHAFT_BROWSER=firefox  →  config.browser.browser = "firefox"
        PYSHAFT_HEADLESS=true    →  config.browser.headless = True

    Args:
        path: Optional explicit path to pyshaft.toml.

    Returns:
        Fully resolved Config object with defaults merged in.
    """
    global _config

    raw: dict[str, Any] = {}
    toml_path = _find_toml(path)

    if toml_path:
        logger.info("Loading config from %s", toml_path)
        raw = _parse_toml(toml_path)
    else:
        logger.info("No pyshaft.toml found — using all defaults")

    config = Config()

    # Merge each TOML section into the corresponding dataclass
    for section_name, dc_class in _SECTION_MAP.items():
        section_data = raw.get(section_name, {})
        section_obj = _merge_section(dc_class, section_data)
        setattr(config, section_name, section_obj)

    # Apply environment variable overrides
    _apply_env_overrides(config)

    # Validate constrained values
    _validate(config)

    _config = config
    return config


def get_config() -> Config:
    """Get the current configuration singleton.

    If not yet loaded, loads with defaults (no file).

    Returns:
        The active Config object.
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """Reset the configuration singleton — mainly for testing."""
    global _config
    _config = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_toml(explicit_path: str | Path | None) -> Path | None:
    """Find pyshaft.toml by searching current dir and parents."""
    if explicit_path:
        p = Path(explicit_path)
        if p.exists():
            return p
        logger.warning("Explicit config path not found: %s", p)
        return None

    current = Path.cwd()
    for directory in [current, *current.parents]:
        candidate = directory / "pyshaft.toml"
        if candidate.exists():
            return candidate

    return None


def _parse_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file and return raw dict."""
    # Python 3.11+ has tomllib built-in; for 3.10, fall back to tomli
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            logger.warning(
                "Neither tomllib (3.11+) nor tomli found. "
                "Install tomli for Python 3.10: pip install tomli"
            )
            return {}

    with open(path, "rb") as f:
        return tomllib.load(f)


def _merge_section(dc_class: type, data: dict[str, Any]) -> Any:
    """Create a dataclass instance, overriding defaults with TOML values."""
    valid_fields = {f.name for f in fields(dc_class)}
    filtered = {}
    for key, value in data.items():
        if key in valid_fields:
            filtered[key] = value
        else:
            logger.warning("Unknown config key [%s].%s — ignored", dc_class.__name__, key)
    return dc_class(**filtered)


def _apply_env_overrides(config: Config) -> None:
    """Apply PYSHAFT_* environment variable overrides.

    Convention: PYSHAFT_<FIELD> maps to the appropriate section.
    We check each section's fields against env vars.
    """
    env_map: dict[str, tuple[str, str]] = {}

    # Build map: ENV_NAME → (section_name, field_name)
    for section_name, dc_class in _SECTION_MAP.items():
        for f in fields(dc_class):
            env_key = f"PYSHAFT_{f.name.upper()}"
            env_map[env_key] = (section_name, f.name)

    for env_key, (section_name, field_name) in env_map.items():
        env_value = os.environ.get(env_key)
        if env_value is None:
            continue

        section_obj = getattr(config, section_name)
        f_obj = next(f for f in fields(section_obj) if f.name == field_name)
        converted = _convert_env_value(env_value, f_obj.type)
        setattr(section_obj, field_name, converted)
        logger.info("Env override: %s = %r", env_key, converted)


def _convert_env_value(value: str, type_hint: str) -> Any:
    """Convert string env value to the target type."""
    match type_hint:
        case "bool":
            return value.lower() in ("true", "1", "yes")
        case "int":
            return int(value)
        case "float":
            return float(value)
        case _:
            return value


def _validate(config: Config) -> None:
    """Validate config values that have constrained options."""
    # Validate browser
    valid_browsers = {b.value for b in BrowserType}
    if config.browser.browser not in valid_browsers:
        raise ConfigError(
            "browser.browser",
            config.browser.browser,
            ", ".join(sorted(valid_browsers)),
        )

    # Validate scope
    valid_scopes = {s.value for s in ScopeType}
    if config.execution.scope not in valid_scopes:
        raise ConfigError(
            "execution.scope",
            config.execution.scope,
            ", ".join(sorted(valid_scopes)),
        )

    # Validate window_size format
    size = config.browser.window_size
    parts = size.lower().split("x")
    if len(parts) != 2 or not all(p.strip().isdigit() for p in parts):
        raise ConfigError(
            "browser.window_size",
            size,
            "WIDTHxHEIGHT (e.g., 1920x1080)",
        )

    # Validate timeouts are positive
    if config.waits.default_element_timeout <= 0:
        raise ConfigError(
            "waits.default_element_timeout",
            str(config.waits.default_element_timeout),
            "positive number",
        )
