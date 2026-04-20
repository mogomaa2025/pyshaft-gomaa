"""Unit tests for PyShaft configuration system."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pyshaft.config import (
    BrowserConfig,
    BrowserType,
    Config,
    ExecutionConfig,
    ScopeType,
    WaitsConfig,
    _convert_env_value,
    _merge_section,
    _parse_toml,
    _validate,
    get_config,
    load_config,
    reset_config,
)
from pyshaft.exceptions import ConfigError


class TestConfigDefaults:
    """Test that all config defaults are sensible."""

    def test_browser_defaults(self) -> None:
        c = BrowserConfig()
        assert c.browser == "chrome"
        assert c.headless is False
        assert c.window_size == "1920x1080"
        assert c.base_url == ""
        assert c.navigation_timeout == 30

    def test_execution_defaults(self) -> None:
        c = ExecutionConfig()
        assert c.parallel is False
        assert c.workers == "auto"
        assert c.retry_attempts == 0
        assert c.scope == "session"

    def test_waits_defaults(self) -> None:
        c = WaitsConfig()
        assert c.default_element_timeout == 10.0
        assert c.polling_interval == 0.25
        assert c.stability_threshold == 0.3
        assert c.respect_native_waits is True

    def test_full_config_defaults(self) -> None:
        c = Config()
        assert c.browser.browser == "chrome"
        assert c.execution.scope == "session"
        assert c.waits.default_element_timeout == 10.0
        assert c.validations.force_element_visibility is True
        assert c.actions.js_click_fallback is True
        assert c.report.screenshot_on_fail is True
        assert c.api.verify_ssl is True


class TestMergeSection:
    """Test TOML section → dataclass merging."""

    def test_merge_with_overrides(self) -> None:
        data = {"browser": "firefox", "headless": True}
        result = _merge_section(BrowserConfig, data)
        assert result.browser == "firefox"
        assert result.headless is True
        assert result.window_size == "1920x1080"  # default preserved

    def test_merge_ignores_unknown_keys(self) -> None:
        data = {"browser": "chrome", "unknown_key": "value"}
        result = _merge_section(BrowserConfig, data)
        assert result.browser == "chrome"

    def test_merge_empty_data(self) -> None:
        result = _merge_section(BrowserConfig, {})
        assert result.browser == "chrome"  # all defaults


class TestConvertEnvValue:
    """Test environment variable type conversion."""

    def test_bool_true(self) -> None:
        assert _convert_env_value("true", "bool") is True
        assert _convert_env_value("1", "bool") is True
        assert _convert_env_value("yes", "bool") is True

    def test_bool_false(self) -> None:
        assert _convert_env_value("false", "bool") is False
        assert _convert_env_value("0", "bool") is False
        assert _convert_env_value("no", "bool") is False

    def test_int(self) -> None:
        assert _convert_env_value("42", "int") == 42

    def test_float(self) -> None:
        assert _convert_env_value("3.14", "float") == pytest.approx(3.14)

    def test_string(self) -> None:
        assert _convert_env_value("firefox", "str") == "firefox"


class TestValidation:
    """Test config validation."""

    def test_valid_config_passes(self) -> None:
        config = Config()
        _validate(config)  # should not raise

    def test_invalid_browser_raises(self) -> None:
        config = Config()
        config.browser.browser = "netscape"
        with pytest.raises(ConfigError, match="browser.browser"):
            _validate(config)

    def test_invalid_scope_raises(self) -> None:
        config = Config()
        config.execution.scope = "global"
        with pytest.raises(ConfigError, match="execution.scope"):
            _validate(config)

    def test_invalid_window_size_raises(self) -> None:
        config = Config()
        config.browser.window_size = "big"
        with pytest.raises(ConfigError, match="browser.window_size"):
            _validate(config)

    def test_negative_timeout_raises(self) -> None:
        config = Config()
        config.waits.default_element_timeout = -1
        with pytest.raises(ConfigError, match="default_element_timeout"):
            _validate(config)


class TestGetConfig:
    """Test the singleton config accessor."""

    def setup_method(self) -> None:
        reset_config()

    def teardown_method(self) -> None:
        reset_config()

    def test_get_config_returns_config(self) -> None:
        config = get_config()
        assert isinstance(config, Config)

    def test_get_config_is_singleton(self) -> None:
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_reset_creates_new_instance(self) -> None:
        c1 = get_config()
        reset_config()
        c2 = get_config()
        assert c1 is not c2


class TestLoadConfig:
    """Test config loading from files and env vars."""

    def setup_method(self) -> None:
        reset_config()

    def teardown_method(self) -> None:
        reset_config()
        # Clean up any env vars we set
        for key in list(os.environ.keys()):
            if key.startswith("PYSHAFT_"):
                del os.environ[key]

    def test_load_with_no_file(self) -> None:
        config = load_config("/nonexistent/path/pyshaft.toml")
        assert isinstance(config, Config)
        assert config.browser.browser == "chrome"  # defaults

    def test_env_override_browser(self) -> None:
        os.environ["PYSHAFT_BROWSER"] = "firefox"
        config = load_config()
        assert config.browser.browser == "firefox"

    def test_env_override_headless(self) -> None:
        os.environ["PYSHAFT_HEADLESS"] = "true"
        config = load_config()
        assert config.browser.headless is True

    def test_env_override_scope(self) -> None:
        os.environ["PYSHAFT_SCOPE"] = "function"
        config = load_config()
        assert config.execution.scope == "function"


class TestEnumValues:
    """Test enum string values match expected config values."""

    def test_browser_types(self) -> None:
        assert BrowserType.CHROME == "chrome"
        assert BrowserType.FIREFOX == "firefox"
        assert BrowserType.EDGE == "edge"

    def test_scope_types(self) -> None:
        assert ScopeType.SESSION == "session"
        assert ScopeType.MODULE == "module"
        assert ScopeType.FUNCTION == "function"
