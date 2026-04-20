"""Unit tests for PyShaft locator engine — detect_mode and resolution chain.

Tests cover:
    - Mode detection (CSS, XPath, semantic, shadow DOM)
    - Prefix stripping
    - Ordinal parsing
    - Strategy chain building
    - Locator cache operations
    - Near/inside/ordinal pattern matching
"""

from __future__ import annotations

import pytest

from pyshaft.core.locator import (
    MultipleMatchWarning,
    _INSIDE_PATTERN,
    _NEAR_PATTERN,
    _ORDINAL_PATTERN,
    _LocatorCache,
    _build_strategy_chain,
    _parse_ordinal,
    detect_mode,
    strip_prefix,
)


# ---------------------------------------------------------------------------
# detect_mode tests
# ---------------------------------------------------------------------------


class TestDetectMode:
    """Test auto-detection of locator mode."""

    # --- CSS signals ---

    def test_css_id_selector(self) -> None:
        assert detect_mode("#login-btn") == "css"

    def test_css_class_selector(self) -> None:
        assert detect_mode(".submit") == "css"

    def test_css_attribute_selector(self) -> None:
        assert detect_mode("[data-testid='login']") == "css"

    def test_css_child_combinator(self) -> None:
        assert detect_mode("> div") == "css"

    def test_css_sibling_combinator(self) -> None:
        assert detect_mode("~ span") == "css"

    def test_css_adjacent_combinator(self) -> None:
        assert detect_mode("+ li") == "css"

    def test_css_pseudo_selector(self) -> None:
        assert detect_mode(":first-child") == "css"

    def test_css_tag_with_class(self) -> None:
        assert detect_mode("div.container") == "css"

    def test_css_tag_with_id(self) -> None:
        assert detect_mode("div#main") == "css"

    def test_css_tag_with_attr(self) -> None:
        assert detect_mode("input[type='text']") == "css"

    # --- CSS explicit prefix ---

    def test_css_explicit_prefix(self) -> None:
        assert detect_mode("css=div.selector") == "css"

    def test_css_prefix_complex(self) -> None:
        assert detect_mode("css=#main > .content") == "css"

    # --- XPath signals ---

    def test_xpath_double_slash(self) -> None:
        assert detect_mode("//button") == "xpath"

    def test_xpath_dot_slash(self) -> None:
        assert detect_mode(".//div[@id='test']") == "xpath"

    def test_xpath_with_attr(self) -> None:
        assert detect_mode("//button[@data-id='submit']") == "xpath"

    def test_xpath_with_text(self) -> None:
        assert detect_mode("//button[contains(text(),'Login')]") == "xpath"

    # --- XPath explicit prefix ---

    def test_xpath_explicit_prefix(self) -> None:
        assert detect_mode("xpath=//div") == "xpath"

    def test_xpath_prefix_complex(self) -> None:
        assert detect_mode("xpath=//form[@id='login']//button") == "xpath"

    # --- Semantic signals ---

    def test_semantic_plain_text(self) -> None:
        assert detect_mode("Login button") == "semantic"

    def test_semantic_single_word(self) -> None:
        assert detect_mode("Login") == "semantic"

    def test_semantic_sentence(self) -> None:
        assert detect_mode("Sign In") == "semantic"

    def test_semantic_with_special_chars(self) -> None:
        assert detect_mode("Search results (10)") == "semantic"

    def test_semantic_empty_string(self) -> None:
        assert detect_mode("") == "semantic"

    def test_semantic_whitespace(self) -> None:
        assert detect_mode("  Hello World  ") == "semantic"

    def test_semantic_with_numbers(self) -> None:
        assert detect_mode("Item 42") == "semantic"

    def test_semantic_email_like(self) -> None:
        assert detect_mode("Email address") == "semantic"

    # --- Semantic explicit prefix ---

    def test_text_explicit_prefix(self) -> None:
        assert detect_mode("text=Login") == "semantic"

    def test_text_prefix_overrides_css(self) -> None:
        assert detect_mode("text=#not-a-css-selector") == "semantic"

    # --- ID prefix ---

    def test_id_prefix(self) -> None:
        assert detect_mode("id=login-btn") == "css"

    # --- Shadow DOM ---

    def test_shadow_dom_basic(self) -> None:
        assert detect_mode("shadow > button") == "shadow"

    def test_shadow_dom_complex(self) -> None:
        assert detect_mode("shadow > #container > button") == "shadow"

    def test_shadow_dom_no_space(self) -> None:
        assert detect_mode("shadow>button") == "shadow"


# ---------------------------------------------------------------------------
# strip_prefix tests
# ---------------------------------------------------------------------------


class TestStripPrefix:
    """Test prefix removal from locator strings."""

    def test_strip_css_prefix(self) -> None:
        assert strip_prefix("css=div.selector") == "div.selector"

    def test_strip_xpath_prefix(self) -> None:
        assert strip_prefix("xpath=//button") == "//button"

    def test_strip_text_prefix(self) -> None:
        assert strip_prefix("text=Login") == "Login"

    def test_strip_id_prefix(self) -> None:
        assert strip_prefix("id=login-btn") == "#login-btn"

    def test_no_prefix_unchanged(self) -> None:
        assert strip_prefix("Login button") == "Login button"

    def test_css_selector_unchanged(self) -> None:
        assert strip_prefix("#login") == "#login"

    def test_xpath_unchanged(self) -> None:
        assert strip_prefix("//button") == "//button"


# ---------------------------------------------------------------------------
# _parse_ordinal tests
# ---------------------------------------------------------------------------


class TestParseOrdinal:
    """Test ordinal word to integer conversion."""

    def test_first(self) -> None:
        assert _parse_ordinal("first") == 1

    def test_second(self) -> None:
        assert _parse_ordinal("second") == 2

    def test_third(self) -> None:
        assert _parse_ordinal("third") == 3

    def test_tenth(self) -> None:
        assert _parse_ordinal("tenth") == 10

    def test_numeric_1st(self) -> None:
        assert _parse_ordinal("1st") == 1

    def test_numeric_2nd(self) -> None:
        assert _parse_ordinal("2nd") == 2

    def test_numeric_3rd(self) -> None:
        assert _parse_ordinal("3rd") == 3

    def test_numeric_21st(self) -> None:
        assert _parse_ordinal("21st") == 21

    def test_case_insensitive(self) -> None:
        assert _parse_ordinal("FIRST") == 1
        assert _parse_ordinal("Third") == 3

    def test_unknown_defaults_to_1(self) -> None:
        assert _parse_ordinal("unknown") == 1


# ---------------------------------------------------------------------------
# Pattern matching tests
# ---------------------------------------------------------------------------


class TestNearPattern:
    """Test 'X near Y' pattern matching."""

    def test_basic_near(self) -> None:
        match = _NEAR_PATTERN.match("button near Email field")
        assert match is not None
        assert match.group(1).strip() == "button"
        assert match.group(2).strip() == "Email field"

    def test_near_case_insensitive(self) -> None:
        match = _NEAR_PATTERN.match("Submit NEAR Password")
        assert match is not None

    def test_near_with_complex_descriptions(self) -> None:
        match = _NEAR_PATTERN.match("Save changes button near Account settings")
        assert match is not None
        assert match.group(1).strip() == "Save changes button"
        assert match.group(2).strip() == "Account settings"

    def test_not_near_pattern(self) -> None:
        match = _NEAR_PATTERN.match("Login button")
        assert match is None


class TestInsidePattern:
    """Test 'X inside Y' pattern matching."""

    def test_basic_inside(self) -> None:
        match = _INSIDE_PATTERN.match("button inside login form")
        assert match is not None
        assert match.group(1).strip() == "button"
        assert match.group(2).strip() == "login form"

    def test_inside_case_insensitive(self) -> None:
        match = _INSIDE_PATTERN.match("Submit INSIDE modal")
        assert match is not None

    def test_inside_complex(self) -> None:
        match = _INSIDE_PATTERN.match("delete icon inside user row")
        assert match is not None
        assert match.group(1).strip() == "delete icon"
        assert match.group(2).strip() == "user row"

    def test_not_inside_pattern(self) -> None:
        match = _INSIDE_PATTERN.match("Login button")
        assert match is None


class TestOrdinalPattern:
    """Test 'Nth X' pattern matching."""

    def test_first_button(self) -> None:
        match = _ORDINAL_PATTERN.match("first submit button")
        assert match is not None
        assert match.group(1) == "first"
        assert match.group(2) == "submit button"

    def test_third_row(self) -> None:
        match = _ORDINAL_PATTERN.match("third row")
        assert match is not None
        assert match.group(1) == "third"
        assert match.group(2) == "row"

    def test_3rd_item(self) -> None:
        match = _ORDINAL_PATTERN.match("3rd item")
        assert match is not None
        assert match.group(1) == "3rd"
        assert match.group(2) == "item"

    def test_21st_element(self) -> None:
        match = _ORDINAL_PATTERN.match("21st element")
        assert match is not None

    def test_not_ordinal(self) -> None:
        match = _ORDINAL_PATTERN.match("Login button")
        assert match is None


# ---------------------------------------------------------------------------
# Strategy chain tests
# ---------------------------------------------------------------------------


class TestBuildStrategyChain:
    """Test the strategy chain builder."""

    def test_chain_not_empty(self) -> None:
        chain = _build_strategy_chain("Login")
        assert len(chain) > 0

    def test_chain_starts_with_aria(self) -> None:
        chain = _build_strategy_chain("Submit")
        names = [name for name, _, _ in chain]
        assert names[0] == "aria_role_name"

    def test_chain_includes_exact_text(self) -> None:
        chain = _build_strategy_chain("Submit")
        names = [name for name, _, _ in chain]
        assert "exact_text" in names

    def test_chain_includes_data_testid(self) -> None:
        chain = _build_strategy_chain("login-form")
        names = [name for name, _, _ in chain]
        assert "data_testid" in names

    def test_chain_includes_id_variants(self) -> None:
        chain = _build_strategy_chain("Login Button")
        names = [name for name, _, _ in chain]
        assert "id_exact_dash" in names
        assert "id_exact_underscore" in names
        assert "id_camel" in names

    def test_chain_camel_case_generation(self) -> None:
        chain = _build_strategy_chain("login button")
        # Find the id_camel entry
        camel_entries = [(n, b, s) for n, b, s in chain if n == "id_camel"]
        assert len(camel_entries) == 1
        assert camel_entries[0][2] == "#loginButton"

    def test_chain_slug_dash(self) -> None:
        chain = _build_strategy_chain("Login Button")
        dash_entries = [(n, b, s) for n, b, s in chain if n == "id_exact_dash"]
        assert len(dash_entries) == 1
        assert dash_entries[0][2] == "#login-button"

    def test_chain_handles_special_chars(self) -> None:
        chain = _build_strategy_chain("Search (results)")
        assert len(chain) > 0

    def test_chain_includes_all_strategy_groups(self) -> None:
        chain = _build_strategy_chain("Submit")
        names = set(name for name, _, _ in chain)
        # Should have strategies from each group
        assert any("aria" in n for n in names)     # Strategy 1
        assert any("text" in n for n in names)      # Strategy 2/3
        assert any("placeholder" in n for n in names)  # Strategy 4
        assert any("data" in n for n in names)      # Strategy 6
        assert any("title" in n for n in names)     # Strategy 7

    def test_empty_selectors_filtered(self) -> None:
        # Single word → no camelCase variant
        chain = _build_strategy_chain("Submit")
        selectors = [s for _, _, s in chain]
        assert "" not in selectors


# ---------------------------------------------------------------------------
# Locator cache tests
# ---------------------------------------------------------------------------


class TestLocatorCache:
    """Test the locator result cache."""

    def test_put_and_get(self) -> None:
        cache = _LocatorCache()
        cache.put("Login", "http://example.com", "css", "#login")
        result = cache.get("Login", "http://example.com")
        assert result == ("css", "#login")

    def test_miss_returns_none(self) -> None:
        cache = _LocatorCache()
        assert cache.get("nonexistent", "http://example.com") is None

    def test_different_urls_different_entries(self) -> None:
        cache = _LocatorCache()
        cache.put("Login", "http://page1.com", "css", "#login1")
        cache.put("Login", "http://page2.com", "css", "#login2")
        assert cache.get("Login", "http://page1.com") == ("css", "#login1")
        assert cache.get("Login", "http://page2.com") == ("css", "#login2")

    def test_clear(self) -> None:
        cache = _LocatorCache()
        cache.put("A", "http://a.com", "css", "#a")
        cache.put("B", "http://b.com", "css", "#b")
        assert cache.size == 2
        cache.clear()
        assert cache.size == 0
        assert cache.get("A", "http://a.com") is None

    def test_eviction_at_max_size(self) -> None:
        cache = _LocatorCache()
        cache.MAX_SIZE = 3

        cache.put("A", "u", "css", "#a")
        cache.put("B", "u", "css", "#b")
        cache.put("C", "u", "css", "#c")
        assert cache.size == 3

        # Adding 4th should evict oldest (A)
        cache.put("D", "u", "css", "#d")
        assert cache.size == 3
        assert cache.get("A", "u") is None
        assert cache.get("D", "u") == ("css", "#d")

    def test_size_property(self) -> None:
        cache = _LocatorCache()
        assert cache.size == 0
        cache.put("X", "u", "css", "#x")
        assert cache.size == 1
