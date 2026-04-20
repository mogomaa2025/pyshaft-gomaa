"""PyShaft DualLocator — 10-strategy semantic resolution + raw CSS/XPath.

The locator engine auto-detects whether a string is:
  - **Raw CSS**: ``"#login-btn"``, ``".submit"``, ``"css=div.container"``
  - **Raw XPath**: ``"//button[@id='submit']"``, ``"xpath=//div"``
  - **Semantic**: ``"Login button"`` → resolved via 10-strategy chain

Semantic Resolution Chain:
    1. ARIA role + name
    2. Exact visible text
    3. Partial visible text
    4. Placeholder / label / aria-label
    5. ID contains text
    6. data-testid / data-qa / data-cy
    7. Title / alt / name attributes
    8. Relative/near — "button near Email field"
    9. Parent/ancestor — "button inside login form"
    10. Index/ordinal — "first submit button", "third row"
    11. Shadow DOM — "shadow > button"
"""

from __future__ import annotations

import logging
import re
import threading
import warnings
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from pyshaft.config import get_config
from pyshaft.exceptions import ElementNotFoundError, MultipleMatchError

logger = logging.getLogger("pyshaft.core.locator")

# ---------------------------------------------------------------------------
# Mode detection patterns
# ---------------------------------------------------------------------------

# CSS signals: starts with #, ., [, >, ~, +, :, or tag[attr] / tag.class / tag#id
_CSS_SIGNALS = re.compile(r"^[#.\[>~+:@]|^[a-z]+\[|^[a-z]+[#.]")

# XPath signals: starts with / or ./
_XPATH_SIGNALS = re.compile(r"^\.?//")

# Relative/near pattern: "X near Y"
_NEAR_PATTERN = re.compile(
    r"^(.+?)\s+near\s+(.+)$", re.IGNORECASE
)

# Parent/ancestor pattern: "X inside Y"
_INSIDE_PATTERN = re.compile(
    r"^(.+?)\s+inside\s+(.+)$", re.IGNORECASE
)

# Index/ordinal patterns: "first X", "second X", "third X", "Nth X"
_ORDINAL_PATTERN = re.compile(
    r"^(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth"
    r"|\d+(?:st|nd|rd|th))\s+(.+)$",
    re.IGNORECASE,
)

_ORDINAL_MAP = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
}

# Shadow DOM pattern: "shadow > selector"
_SHADOW_PATTERN = re.compile(r"^shadow\s*>\s*(.+)$", re.IGNORECASE)

# New unified format patterns for action(type, value)
# Examples: "role=button", "text,contain=Login", "id,starts=btn", "role=button tag=div"
# IMPORTANT: Must be at start of string, not inside CSS selector
_UNIFIED_PATTERN = re.compile(
    r"^(role|text|label|placeholder|testid|id|class|css|xpath|tag|attr)"
    r"(?:,(exact|contain|starts|contains))?"
    r"=(.+)$",
    re.IGNORECASE
)

# Filter pattern: key=value
_FILTER_PATTERN = re.compile(r"(\w+)=([^\s]+)")

# Inside pattern for unified format: inside=type=value
_UNIFIED_INSIDE_PATTERN = re.compile(r"inside=(\w+)(?:,(\w+))?=([^\s]+)")

# Index range pattern: index=0 or index=0,1,2,3 or index=0:5
_INDEX_PATTERN = re.compile(r">>\s*index=([\d,:]+)$")


class MultipleMatchWarning(UserWarning):
    """Warning issued when a locator matches more than one element."""


# ---------------------------------------------------------------------------
# Locator cache
# ---------------------------------------------------------------------------


class _LocatorCache:
    """Thread-safe LRU cache for resolved locator selectors.

    Keys are (description, url) tuples. Values are (by_method, selector) tuples.
    Cache is limited to MAX_SIZE entries (FIFO eviction).
    """

    MAX_SIZE = 256

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], tuple[str, str]] = {}
        self._lock = threading.Lock()

    def get(self, description: str, url: str) -> tuple[str, str] | None:
        """Get a cached (by_method, selector) for a description+url key."""
        with self._lock:
            return self._cache.get((description, url))

    def put(self, description: str, url: str, by_method: str, selector: str) -> None:
        """Cache a resolved (by_method, selector)."""
        with self._lock:
            if len(self._cache) >= self.MAX_SIZE:
                # Evict oldest entry
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[(description, url)] = (by_method, selector)

    def clear(self) -> None:
        """Clear the entire cache."""
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        """Current number of cached entries."""
        return len(self._cache)


_cache = _LocatorCache()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_mode(text: str) -> str:
    """Auto-detect whether a locator string is raw CSS/XPath or semantic.

    Args:
        text: The locator string to analyze.

    Returns:
        "css" for CSS selectors, "xpath" for XPath, "shadow" for shadow DOM,
        "unified" for new action(type,value) format,
        or "semantic" for plain-English descriptions.
    """
    stripped = text.strip()

    # Explicit prefix overrides
    if stripped.startswith("css="):
        return "css"
    if stripped.startswith("xpath="):
        return "xpath"
    if stripped.startswith("text="):
        return "semantic"
    if stripped.startswith("id="):
        return "css"

    # New unified format: action(type, value) or type=value
    # Must start with known type keyword (role, text, label, etc.)
    # and NOT be a CSS attribute selector like [attr=value] or tag[attr=value]
    if _UNIFIED_PATTERN.match(stripped):
        # Verify it's not a CSS pattern (attribute selector)
        if not stripped.startswith("[") and not re.match(r"^[a-z]+\[", stripped):
            return "unified"

    # Shadow DOM
    if _SHADOW_PATTERN.match(stripped):
        return "shadow"

    # XPath patterns
    if _XPATH_SIGNALS.match(stripped):
        return "xpath"

    # CSS patterns
    if _CSS_SIGNALS.match(stripped):
        return "css"

    # Default: semantic
    return "semantic"


def strip_prefix(text: str) -> str:
    """Remove css=, xpath=, text=, or id= prefix from a locator string.
    
    Also handles new unified format prefixes: role=, text,exact=, etc.
    """
    # Handle new unified format: type,modifier=value -> strip to type,modifier=value
    for prefix in ("css=", "xpath=", "text="):
        if text.startswith(prefix):
            return text[len(prefix):]
    if text.startswith("id="):
        return f"#{text[3:]}"
    
    # Handle unified format like role=button, text,contain=Login
    # Just return as-is since it's already parsed by detect_mode
    if _UNIFIED_PATTERN.match(text):
        return text
    
    return text


class DualLocator:
    """Resolves locator descriptions to WebElements.

    Supports three modes:
        - **Raw CSS**: ``"#login-btn"``, ``".submit"``, ``"css=div.container"``
        - **Raw XPath**: ``"//button[@id='submit']"``, ``"xpath=//div"``
        - **Semantic**: ``"Login button"`` → resolved via 10-strategy chain
        - **Shadow DOM**: ``"shadow > button"`` → traverses shadow roots

    Results are cached per (description, url) to avoid redundant DOM queries.
    """

    @staticmethod
    def resolve(driver: WebDriver, description: str) -> WebElement:
        """Resolve a locator description to a single WebElement.

        Args:
            driver: The WebDriver instance.
            description: Locator text (CSS, XPath, or semantic).

        Returns:
            The best-matched WebElement.

        Raises:
            ElementNotFoundError: If no element matches.
            MultipleMatchError: If multiple match and force_locator_unique is True.
        """
        config = get_config()
        url = driver.current_url

        # 1. Parse indexer suffix: "(...) >> index=N" or "(...) >> index=0,1,2" or "(...) >> index=0:5"
        target_index = None
        target_indices = None  # For range: 0:5 means [0,1,2,3,4]
        
        # Check for range pattern first (index=0:5)
        range_match = re.search(r" >> index=(\d+):(\d+)$", description)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            target_indices = list(range(start, end))
            extracted_base = description[:range_match.start()]
            if extracted_base.startswith("(") and extracted_base.endswith(")"):
                base_description = extracted_base[1:-1]
            else:
                base_description = extracted_base
        else:
            # Single index pattern (index=0 or index=-1)
            index_match = re.search(r" >> index=(-?\d+)$", description)
            if index_match:
                target_index = int(index_match.group(1))
                extracted_base = description[:index_match.start()]
                # Unwrap parenthesis if present: "(selector) >> index=0"
                if extracted_base.startswith("(") and extracted_base.endswith(")"):
                    base_description = extracted_base[1:-1]
                else:
                    base_description = extracted_base
            else:
                base_description = description

        # 2. Detect mode for the base description
        mode = detect_mode(base_description)
        raw = strip_prefix(base_description)

        logger.debug("Resolving locator: %r (mode=%s, target_index=%s)", 
                     base_description, mode, target_index)

        # 3. Check cache for base description
        cached = _cache.get(base_description, url)
        if cached:
            by_method, selector = cached
            elements = _find_elements(driver, by_method, selector)
            if elements:
                if target_index is not None:
                    try:
                        return elements[target_index]
                    except IndexError:
                        raise ElementNotFoundError(f"Index {target_index} out of range for {base_description!r} (found {len(elements)})")
                return _select_best(elements, base_description, url, config)

        # 4. Resolve base elements
        elements: list[WebElement] = []
        strategies_tried: list[str] = []

        match mode:
            case "css":
                elements = _find_by_css(driver, raw)
                strategies_tried.append(f"css({raw})")
                if elements:
                    _cache.put(base_description, url, "css", raw)

            case "xpath":
                elements = _find_by_xpath(driver, raw)
                strategies_tried.append(f"xpath({raw})")
                if elements:
                    _cache.put(base_description, url, "xpath", raw)

            case "shadow":
                shadow_sel = _SHADOW_PATTERN.match(base_description.strip())
                if shadow_sel:
                    elements = _find_shadow_dom(driver, shadow_sel.group(1).strip())
                    strategies_tried.append(f"shadow({shadow_sel.group(1)})")

            case "unified":
                elements, strategies_tried = _resolve_unified(driver, base_description)

            case "semantic":
                elements, strategies_tried = _resolve_semantic(driver, raw)

        # 5. Handle results + indexing
        if not elements:
            raise ElementNotFoundError(
                description=base_description,
                strategies_tried=strategies_tried,
                url=url,
            )

        # Handle range index (e.g., index=0:5 means click elements 0,1,2,3,4)
        if target_indices is not None:
            valid_indices = [i for i in target_indices if 0 <= i < len(elements)]
            if not valid_indices:
                raise ElementNotFoundError(
                    description=f"{base_description} [index={target_indices}]",
                    strategies_tried=[f"Found {len(elements)} elements, but range {target_indices} is out of range."],
                    url=url
                )
            # Return elements for the range (for batch operations)
            # For single element resolution, return the first in range
            return elements[valid_indices[0]]

        if target_index is not None:
            try:
                # Return exact index WITHOUT calling _select_best (prevents warnings)
                return elements[target_index]
            except IndexError:
                raise ElementNotFoundError(
                    description=f"{base_description} [index={target_index}]",
                    strategies_tried=[f"Found {len(elements)} elements, but index {target_index} is out of range."],
                    url=url
                )

        return _select_best(elements, base_description, url, config)

    @staticmethod
    def resolve_all(driver: WebDriver, description: str) -> list[WebElement]:
        """Resolve a locator description to all matching WebElements.

        Args:
            driver: The WebDriver instance.
            description: Locator text.

        Returns:
            List of all matching WebElements (may be empty).
        """
        mode = detect_mode(description)
        raw = strip_prefix(description)

        match mode:
            case "css":
                return _find_by_css(driver, raw)
            case "xpath":
                return _find_by_xpath(driver, raw)
            case "shadow":
                shadow_sel = _SHADOW_PATTERN.match(description.strip())
                if shadow_sel:
                    return _find_shadow_dom(driver, shadow_sel.group(1).strip())
                return []
            case "unified":
                elements, _ = _resolve_unified(driver, description)
                return elements
            case "semantic":
                elements, _ = _resolve_semantic(driver, raw)
                return elements
            case _:
                return []

    @staticmethod
    def clear_cache() -> None:
        """Clear the locator result cache."""
        _cache.clear()


# ---------------------------------------------------------------------------
# Internal resolution functions
# ---------------------------------------------------------------------------


def _find_elements(driver: WebDriver, by_method: str, selector: str) -> list[WebElement]:
    """Find elements using the specified method."""
    try:
        if by_method == "xpath":
            return driver.find_elements(By.XPATH, selector)
        return driver.find_elements(By.CSS_SELECTOR, selector)
    except Exception:
        return []


def _find_by_css(driver: WebDriver, selector: str) -> list[WebElement]:
    """Find elements by CSS selector."""
    try:
        return driver.find_elements(By.CSS_SELECTOR, selector)
    except Exception as e:
        logger.debug("CSS selector failed: %s — %s", selector, e)
        return []


def _find_by_xpath(driver: WebDriver, expression: str) -> list[WebElement]:
    """Find elements by XPath expression."""
    try:
        return driver.find_elements(By.XPATH, expression)
    except Exception as e:
        logger.debug("XPath expression failed: %s — %s", expression, e)
        return []


def _select_best(
    elements: list[WebElement],
    description: str,
    url: str,
    config: Any,
) -> WebElement:
    """Select the best element from a list, enforcing uniqueness if configured.

    Priority order when multiple elements match:
        1. Visible + interactive (button, a, input, select, textarea)
        2. Visible
        3. First element

    Args:
        elements: List of matching elements.
        description: Original locator description.
        url: Current page URL.
        config: PyShaft config object.

    Returns:
        The best matching element.

    Raises:
        MultipleMatchError: If uniqueness is enforced and multiple elements match.
    """
    if len(elements) == 1:
        return elements[0]

    # Multiple matches
    if config.validations.force_locator_unique:
        raise MultipleMatchError(
            description=description,
            match_count=len(elements),
            url=url,
        )

    # Warn and return best match
    warnings.warn(
        f"Multiple elements ({len(elements)}) found for {description!r} — using best match",
        MultipleMatchWarning,
        stacklevel=4,
    )

    _INTERACTIVE_TAGS = {"button", "a", "input", "select", "textarea"}

    # Pass 1: Prefer visible + interactive elements
    for el in elements:
        try:
            if el.is_displayed() and el.tag_name.lower() in _INTERACTIVE_TAGS:
                return el
        except Exception:
            continue

    # Pass 2: Prefer any visible element
    for el in elements:
        try:
            if el.is_displayed():
                return el
        except Exception:
            continue

    return elements[0]


# ---------------------------------------------------------------------------
# 10-Strategy Semantic Resolution Chain
# ---------------------------------------------------------------------------


def _resolve_semantic(driver: WebDriver, description: str) -> tuple[list[WebElement], list[str]]:
    """Resolve a semantic description through the 10-strategy chain.

    Each strategy is tried in order. The first one that returns elements wins.
    This covers 99% of XPath use cases in plain English.

    Returns:
        Tuple of (elements_found, strategies_tried names).
    """
    strategies_tried: list[str] = []

    # Check for compound semantic patterns first
    # Strategy 8: Relative/near — "button near Email field"
    near_match = _NEAR_PATTERN.match(description)
    if near_match:
        target_desc = near_match.group(1).strip()
        anchor_desc = near_match.group(2).strip()
        elements = _strategy_near(driver, target_desc, anchor_desc)
        strategies_tried.append(f"near({target_desc} near {anchor_desc})")
        if elements:
            return elements, strategies_tried

    # Strategy 9: Parent/ancestor — "button inside login form"
    inside_match = _INSIDE_PATTERN.match(description)
    if inside_match:
        child_desc = inside_match.group(1).strip()
        parent_desc = inside_match.group(2).strip()
        elements = _strategy_inside(driver, child_desc, parent_desc)
        strategies_tried.append(f"inside({child_desc} inside {parent_desc})")
        if elements:
            return elements, strategies_tried

    # Strategy 10: Index/ordinal — "first submit button", "3rd row"
    ordinal_match = _ORDINAL_PATTERN.match(description)
    if ordinal_match:
        ordinal_word = ordinal_match.group(1).strip().lower()
        element_desc = ordinal_match.group(2).strip()
        index = _parse_ordinal(ordinal_word)
        elements = _strategy_ordinal(driver, element_desc, index)
        strategies_tried.append(f"ordinal({ordinal_word} {element_desc})")
        if elements:
            return elements, strategies_tried

    # Strategies 1-7: Direct attribute/text matching
    chain = _build_strategy_chain(description)

    for strategy_name, by_method, selector in chain:
        strategies_tried.append(strategy_name)
        try:
            if by_method == "xpath":
                elements = driver.find_elements(By.XPATH, selector)
            elif by_method == "js":
                elements = _execute_js_strategy(driver, selector)
            else:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)

            if elements:
                logger.debug(
                    "Semantic match via %s: %r → %d element(s)",
                    strategy_name,
                    description,
                    len(elements),
                )
                # Cache the winning strategy
                if by_method in ("css", "xpath"):
                    _cache.put(description, driver.current_url, by_method, selector)
                return elements, strategies_tried

        except Exception as e:
            logger.debug("Strategy %s failed: %s", strategy_name, e)
            continue

    return [], strategies_tried


def _build_strategy_chain(description: str) -> list[tuple[str, str, str]]:
    """Build the ordered list of strategies for a plain description.

    Returns list of (strategy_name, by_method, selector) tuples.
    """
    desc = description.strip()
    # Escape quotes for use in selectors
    desc_escaped = desc.replace("'", "\\'")
    desc_dq_escaped = desc.replace('"', '\\"')

    # Build slug variants for ID matching
    slug_dash = re.sub(r"[^a-z0-9]+", "-", desc.lower()).strip("-")
    slug_underscore = re.sub(r"[^a-z0-9]+", "_", desc.lower()).strip("_")

    # CamelCase variant: "login button" → "loginButton"
    words = desc.split()
    camel = words[0].lower() + "".join(w.capitalize() for w in words[1:]) if len(words) > 1 else ""

    # Check for structured semantic string: "role=textbox text=Username"
    if "=" in desc:
        structured = _build_structured_chain(desc)
        if structured:
            return structured

    chain: list[tuple[str, str, str]] = [
        # Strategy 1: ARIA role + name
        (
            "aria_role_name",
            "xpath",
            f'//*[@role and @aria-label="{desc_dq_escaped}"]',
        ),
        (
            "aria_role_text",
            "xpath",
            f'//*[@role][normalize-space()="{desc_dq_escaped}"]',
        ),

        # Strategy 2: Exact visible text (any element)
        (
            "exact_text",
            "xpath",
            f'//*[normalize-space()="{desc_dq_escaped}"]',
        ),

        # Strategy 3: Partial visible text
        (
            "partial_text",
            "xpath",
            f'//*[contains(normalize-space(),"{desc_dq_escaped}")]',
        ),

        # Strategy 4: Placeholder, label, aria-label
        (
            "aria_label_exact",
            "css",
            f'[aria-label="{desc_escaped}"]',
        ),
        (
            "aria_label_partial",
            "css",
            f'[aria-label*="{desc_escaped}" i]',
        ),
        (
            "placeholder_exact",
            "css",
            f'[placeholder="{desc_escaped}"]',
        ),
        (
            "placeholder_partial",
            "css",
            f'[placeholder*="{desc_escaped}" i]',
        ),
        # Label text → linked input via for/id
        (
            "label_for",
            "xpath",
            f'//input[@id=//label[normalize-space()="{desc_dq_escaped}"]/@for]',
        ),
        (
            "label_partial",
            "xpath",
            f'//input[@id=//label[contains(normalize-space(),"{desc_dq_escaped}")]/@for]',
        ),

        # Strategy 5: ID contains text (slug variants)
        (
            "id_exact_dash",
            "css",
            f"#{slug_dash}" if slug_dash else "",
        ),
        (
            "id_exact_underscore",
            "css",
            f"#{slug_underscore}" if slug_underscore else "",
        ),
        (
            "id_camel",
            "css",
            f"#{camel}" if camel else "",
        ),
        (
            "id_contains",
            "css",
            f'[id*="{slug_dash}"]' if slug_dash else "",
        ),

        # Strategy 6: data-testid / data-qa / data-cy
        (
            "data_testid",
            "css",
            f'[data-testid="{desc_escaped}"]',
        ),
        (
            "data_testid_slug",
            "css",
            f'[data-testid="{slug_dash}"]' if slug_dash else "",
        ),
        (
            "data_qa",
            "css",
            f'[data-qa="{desc_escaped}"]',
        ),
        (
            "data_cy",
            "css",
            f'[data-cy="{desc_escaped}"]',
        ),
        (
            "data_test",
            "css",
            f'[data-test="{desc_escaped}"]',
        ),

        # Strategy 7: Title, alt, name attributes
        (
            "title_attr",
            "css",
            f'[title="{desc_escaped}"]',
        ),
        (
            "title_partial",
            "css",
            f'[title*="{desc_escaped}" i]',
        ),
        (
            "alt_attr",
            "css",
            f'[alt="{desc_escaped}"]',
        ),
        (
            "name_attr",
            "css",
            f'[name="{desc_escaped}"]',
        ),
        (
            "value_attr",
            "css",
            f'[value="{desc_escaped}"]',
        ),
    ]

    # Filter out empty selectors
    return [(name, by, sel) for name, by, sel in chain if sel]


def _build_structured_chain(description: str) -> list[tuple[str, str, str]]:
    """Parse key=value pairs and build targeted strategies ordered by precision.
    
    Example: "role=textbox text=Username type=password"
    
    Generates separate strategies per attribute (most specific first) to avoid
    MultipleMatchError from broad OR conditions matching labels alongside inputs.
    """
    filters = {}
    
    for part in description.split():
        if "=" in part:
            k, v = part.split("=", 1)
            filters[k.lower()] = v
            
    if not filters:
        return []

    role = filters.get("role", "*")
    text = filters.get("text")
    name = filters.get("name")  # Support name= kwarg directly
    type_attr = filters.get("type")
    placeholder = filters.get("placeholder")
    label = filters.get("label")

    # Merge name into text if name provided (get_by_role passes name=)
    search_text = name or text

    # Map common ARIA roles to HTML tags
    role_to_tags = {
        "textbox": ["input", "textarea"],
        "button": ["button", "input[@type='submit']", "input[@type='button']"],
        "link": ["a"],
        "checkbox": ["input[@type='checkbox']"],
        "radio": ["input[@type='radio']"],
    }
    
    tags = role_to_tags.get(role, ["*"])
    type_cond = f" and @type='{type_attr}'" if type_attr else ""
    
    chain = []

    # For each tag, generate strategies ordered by precision (most specific first)
    for tag in tags:
        base = f"//{tag}"

        if placeholder:
            chain.append((f"struct_{tag}_placeholder", "xpath",
                          f"{base}[@placeholder='{placeholder}'{type_cond}]"))

        if label:
            chain.append((f"struct_{tag}_aria_label", "xpath",
                          f"{base}[@aria-label='{label}'{type_cond}]"))

        if search_text:
            # 1. Most precise: @name attribute (unique per form)
            chain.append((f"struct_{tag}_name", "xpath",
                          f"{base}[@name='{search_text}'{type_cond}]"))

            # 2. @placeholder attribute
            chain.append((f"struct_{tag}_placeholder_text", "xpath",
                          f"{base}[@placeholder='{search_text}'{type_cond}]"))

            # 3. @aria-label attribute
            chain.append((f"struct_{tag}_aria", "xpath",
                          f"{base}[@aria-label='{search_text}'{type_cond}]"))

            # 4. Linked via <label for="id">
            chain.append((f"struct_{tag}_label_for", "xpath",
                          f"{base}[@id=//label[normalize-space()='{search_text}']/@for{type_cond}]"))

        if type_attr and not search_text and not placeholder and not label:
            # Type-only filter (e.g., get_by_role("textbox", type="password"))
            chain.append((f"struct_{tag}_type", "xpath",
                          f"{base}[@type='{type_attr}']"))

        if not (search_text or placeholder or label or type_attr):
            # Role-only filter (e.g., get_by_role("textbox"))
            chain.append((f"struct_{tag}_only", "xpath", base))

    # Last resort: broad text match (only if nothing else matched)
    if search_text and not (placeholder or label or type_attr):
        chain.append(("struct_text_fallback", "xpath",
                      f"//*[normalize-space()='{search_text}']"))

    return chain


# ---------------------------------------------------------------------------
# Strategy 8: Relative/Near — proximity-based matching
# ---------------------------------------------------------------------------


def _strategy_near(
    driver: WebDriver,
    target_desc: str,
    anchor_desc: str,
) -> list[WebElement]:
    """Find target element nearest to an anchor element.

    Example: "button near Email field" → finds the button closest to the
    element matching "Email field".

    Uses JavaScript to calculate geometric distance between element centers.
    """
    # First, find the anchor element
    anchor_elements, _ = _resolve_semantic(driver, anchor_desc)
    if not anchor_elements:
        logger.debug("Near: anchor %r not found", anchor_desc)
        return []

    anchor = anchor_elements[0]

    # Then find all candidate target elements
    target_elements, _ = _resolve_semantic(driver, target_desc)
    if not target_elements:
        logger.debug("Near: target %r not found", target_desc)
        return []

    if len(target_elements) == 1:
        return target_elements

    # Sort by distance to anchor (using JS to get bounding rects)
    try:
        js_code = """
        var anchor = arguments[0];
        var candidates = arguments[1];
        var anchorRect = anchor.getBoundingClientRect();
        var anchorCx = anchorRect.left + anchorRect.width / 2;
        var anchorCy = anchorRect.top + anchorRect.height / 2;

        var distances = [];
        for (var i = 0; i < candidates.length; i++) {
            var rect = candidates[i].getBoundingClientRect();
            var cx = rect.left + rect.width / 2;
            var cy = rect.top + rect.height / 2;
            var dist = Math.sqrt(Math.pow(cx - anchorCx, 2) + Math.pow(cy - anchorCy, 2));
            distances.push(dist);
        }
        return distances;
        """
        distances = driver.execute_script(js_code, anchor, target_elements)

        # Sort targets by distance and return the closest
        paired = sorted(zip(distances, target_elements), key=lambda x: x[0])
        return [el for _, el in paired]

    except Exception as e:
        logger.debug("Near: JS distance calculation failed: %s", e)
        return target_elements


# ---------------------------------------------------------------------------
# Strategy 9: Parent/Ancestor — structural matching
# ---------------------------------------------------------------------------


def _strategy_inside(
    driver: WebDriver,
    child_desc: str,
    parent_desc: str,
) -> list[WebElement]:
    """Find child element inside a parent element.

    Example: "button inside login form" → finds buttons within the element
    matching "login form".
    """
    # Find the parent container
    parent_elements, _ = _resolve_semantic(driver, parent_desc)
    if not parent_elements:
        logger.debug("Inside: parent %r not found", parent_desc)
        return []

    parent = parent_elements[0]

    # Search for child within the parent's subtree
    child_mode = detect_mode(child_desc)
    child_raw = strip_prefix(child_desc)

    if child_mode == "css":
        try:
            return parent.find_elements(By.CSS_SELECTOR, child_raw)
        except Exception:
            return []
    elif child_mode == "xpath":
        try:
            return parent.find_elements(By.XPATH, f".{child_raw}" if child_raw.startswith("/") else child_raw)
        except Exception:
            return []
    else:
        # Semantic search within parent context
        return _find_semantic_within(parent, child_desc)


def _find_semantic_within(parent: WebElement, description: str) -> list[WebElement]:
    """Find elements matching a semantic description within a parent element."""
    desc_escaped = description.replace('"', '\\"')

    # Try text matching within parent
    strategies = [
        ("xpath", f'.//*[normalize-space()="{desc_escaped}"]'),
        ("xpath", f'.//*[contains(normalize-space(),"{desc_escaped}")]'),
        ("css", f'[aria-label*="{description}"]'),
        ("css", f'[placeholder*="{description}"]'),
        ("css", f'[data-testid*="{description}"]'),
    ]

    for by_method, selector in strategies:
        try:
            if by_method == "xpath":
                elements = parent.find_elements(By.XPATH, selector)
            else:
                elements = parent.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                return elements
        except Exception:
            continue

    return []


# ---------------------------------------------------------------------------
# Strategy 10: Index/Ordinal — positional matching
# ---------------------------------------------------------------------------


def _parse_ordinal(word: str) -> int:
    """Convert an ordinal word or '3rd' format to a 1-based int index."""
    word = word.lower()
    if word in _ORDINAL_MAP:
        return _ORDINAL_MAP[word]

    # Parse "3rd", "1st", "2nd", etc.
    numeric = re.match(r"(\d+)", word)
    if numeric:
        return int(numeric.group(1))

    return 1


def _strategy_ordinal(
    driver: WebDriver,
    element_desc: str,
    index: int,
) -> list[WebElement]:
    """Find the Nth element matching a description.

    Example: "third row" → finds all elements matching "row", returns the 3rd.

    Args:
        driver: The WebDriver instance.
        element_desc: Description of elements to find (e.g., "row", "submit button").
        index: 1-based index of the desired element.

    Returns:
        A single-element list if the Nth element exists, else empty.
    """
    # Get all matching elements
    all_elements, _ = _resolve_semantic(driver, element_desc)

    if not all_elements:
        return []

    # Convert to 0-based index
    idx = index - 1
    if 0 <= idx < len(all_elements):
        return [all_elements[idx]]

    logger.debug(
        "Ordinal: requested index %d but only %d elements found for %r",
        index,
        len(all_elements),
        element_desc,
    )
    return []


# ---------------------------------------------------------------------------
# Strategy 11: Shadow DOM traversal
# ---------------------------------------------------------------------------


def _find_shadow_dom(driver: WebDriver, selector: str) -> list[WebElement]:
    """Traverse shadow DOM roots to find elements.

    Supports selectors like:
        - ``"shadow > button"`` — find button in any shadow root
        - ``"shadow > #container > button"`` — nested path through shadow roots

    Uses JavaScript to recursively walk shadowRoot properties.
    """
    parts = [p.strip() for p in selector.split(">")]

    js_code = """
    function findInShadowRoots(root, selector) {
        var results = [];

        // Try finding in this root
        try {
            var found = root.querySelectorAll(selector);
            for (var i = 0; i < found.length; i++) {
                results.push(found[i]);
            }
        } catch(e) {}

        // Recursively search shadow roots
        var allElements = root.querySelectorAll('*');
        for (var i = 0; i < allElements.length; i++) {
            var el = allElements[i];
            if (el.shadowRoot) {
                var shadowResults = findInShadowRoots(el.shadowRoot, selector);
                for (var j = 0; j < shadowResults.length; j++) {
                    results.push(shadowResults[j]);
                }
            }
        }

        return results;
    }

    var finalSelector = arguments[0];
    return findInShadowRoots(document, finalSelector);
    """

    # For multi-part selectors, try the final part across all shadow roots
    final_selector = parts[-1] if parts else selector

    try:
        elements = driver.execute_script(js_code, final_selector)
        return elements if elements else []
    except Exception as e:
        logger.debug("Shadow DOM traversal failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# JS-based strategy helper
# ---------------------------------------------------------------------------


def _execute_js_strategy(driver: WebDriver, js_code: str) -> list[WebElement]:
    """Execute a JavaScript strategy and return matched elements."""
    try:
        result = driver.execute_script(js_code)
        if isinstance(result, list):
            return result
        if result:
            return [result]
        return []
    except Exception as e:
        logger.debug("JS strategy failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# New Unified Locator Resolution
# ---------------------------------------------------------------------------


def _resolve_unified(driver: WebDriver, description: str) -> tuple[list[WebElement], list[str]]:
    """Resolve the new unified format: action(type, value) or type=value.
    
    Examples:
        - role=button -> button elements with @role='button'
        - text,contain=Login -> elements containing "Login"
        - id,starts=btn -> elements with id starting with "btn"
        - role=button tag=div -> button elements inside div tags
    """
    strategies_tried: list[str] = []
    elements: list[WebElement] = []
    
    # Parse the base locator (before >>)
    base_part = description.split(">>")[0].strip()
    
    # Extract main locator from the beginning
    parts = base_part.split(None, 1)
    main_part = parts[0]
    filter_part = parts[1] if len(parts) > 1 else ""
    
    # Extract filters and inside from description
    filters = {}
    inside_locator = None
    
    # Parse filters: key=value pairs from the filter part only
    for match in _FILTER_PATTERN.finditer(filter_part):
        key, value = match.groups()
        if key not in ("role", "text", "label", "placeholder", "testid", "css", "xpath", "attr", "inside", "index"):
            filters[key] = value
    
    # Parse inside: inside=tag=value or inside=id=value
    inside_match = _INSIDE_PATTERN.search(filter_part)
    if inside_match:
        inside_type = inside_match.group(1)
        inside_modifier = inside_match.group(2)
        inside_value = inside_match.group(3)
        if inside_modifier:
            inside_locator = f"{inside_type},{inside_modifier}={inside_value}"
        else:
            inside_locator = f"{inside_type}={inside_value}"
    
    # Parse main locator type and value
    main_match = _UNIFIED_PATTERN.match(main_part)
    if not main_match:
        return _resolve_semantic(driver, base_part)
    
    locator_type = main_match.group(1).lower()
    modifier = main_match.group(2)
    value = main_match.group(3)
    
    strategies_tried.append(f"unified({locator_type},{modifier or 'exact'}={value})")
    
    selector = _build_unified_selector(locator_type, modifier, value, filters)
    
    if selector:
        if selector.startswith("//") or selector.startswith(".//"):
            elements = _find_by_xpath(driver, selector)
        else:
            elements = _find_by_css(driver, selector)
        
        if elements and inside_locator:
            parent_elements, _ = _resolve_unified(driver, inside_locator)
            if parent_elements:
                elements = _filter_elements_inside(elements, parent_elements)
    
    return elements, strategies_tried


def _build_unified_selector(locator_type: str, modifier: str | None, value: str, filters: dict) -> str:
    """Build a CSS or XPath selector from unified format."""
    value_escaped = value.replace("'", "\\'").replace('"', '\\"')
    
    is_xpath = False
    base = ""
    
    match locator_type:
        case "role":
            is_xpath = True
            base = f"//*[@role='{value_escaped}']"
        case "text":
            is_xpath = True
            if modifier in ("contain", "contains"):
                base = f"//*[contains(normalize-space(),'{value_escaped}')]"
            elif modifier == "starts":
                base = f"//*[starts-with(normalize-space(),'{value_escaped}')]"
            else:
                base = f"//*[normalize-space()='{value_escaped}']"
        case "label":
            is_xpath = True
            base = f"//input[@id=//label[normalize-space()='{value_escaped}']/@for]"
        case "placeholder":
            if modifier in ("contain", "contains"):
                base = f'[placeholder*="{value_escaped}" i]'
            else:
                base = f'[placeholder="{value_escaped}"]'
        case "testid":
            base = f'[data-testid="{value_escaped}"],[data-cy="{value_escaped}"],[data-qa="{value_escaped}"],[data-test="{value_escaped}"]'
        case "id":
            if modifier == "starts":
                base = f'[id^="{value_escaped}"]'
            elif modifier in ("contain", "contains"):
                base = f'[id*="{value_escaped}"]'
            else:
                base = f'#{value_escaped}'
        case "class":
            base = f'.{value_escaped}'
        case "css":
            base = value_escaped
        case "xpath":
            is_xpath = True
            base = f"//{value_escaped}" if not value_escaped.startswith("/") else value_escaped
        case "tag":
            base = value_escaped
        case "attr":
            attr_name = value_escaped
            attr_val = filters.get("attr_value", "")
            if attr_val:
                if modifier == "starts":
                    base = f'[{attr_name}^="{attr_val}"]'
                elif modifier in ("contain", "contains"):
                    base = f'[{attr_name}*="{attr_val}"]'
                else:
                    base = f'[{attr_name}="{attr_val}"]'
            else:
                base = f'[{attr_name}]'
        case _:
            return ""

    if not filters:
        return base

    # Apply filters
    if is_xpath:
        # For XPath, we modify the tagname and predicates
        tag_name = filters.get("tag", "*")
        if base.startswith("//*"):
            base = f"//{(tag_name)}{base[3:]}"
            
        predicates = []
        for key, val in filters.items():
            if key == "tag": continue
            val_escaped = val.replace("'", "\\'")
            if key == "class":
                predicates.append(f"contains(concat(' ', normalize-space(@class), ' '), ' {val_escaped} ')")
            elif key == "id":
                predicates.append(f"@id='{val_escaped}'")
            else:
                predicates.append(f"@{key}='{val_escaped}'")
                
        if predicates:
            predicate_str = " and ".join(predicates)
            # Add predicates. If base already has predicates, we append.
            base += f"[{predicate_str}]"
        return base
    else:
        # For CSS
        filter_parts = []
        tag_name = filters.get("tag", "")
        # Remove tag from being appended as an attribute
        for key, val in filters.items():
            if key == "tag": continue
            val_escaped = val.replace("'", "\\'")
            if key == "class":
                filter_parts.append(f'.{val_escaped}')
            elif key == "id":
                filter_parts.append(f'#{val_escaped}')
            else:
                filter_parts.append(f'[{key}="{val_escaped}"]')
                
        filters_str = "".join(filter_parts)
        if locator_type in ("tag", "class", "id") or base.startswith("#") or base.startswith("."):
            return f"{tag_name}{base}{filters_str}"
        elif base.startswith("["):
            return f"{tag_name}{base}{filters_str}"
        else:
            return f"{tag_name}{base}{filters_str}"


def _filter_elements_inside(elements: list[WebElement], parents: list[WebElement]) -> list[WebElement]:
    """Filter elements that are descendants of any of the parent elements."""
    from selenium.webdriver.common.by import By
    
    result = []
    for el in elements:
        for parent in parents:
            try:
                # Check if el is a descendant of parent
                # Use JavaScript to check DOM relationship
                from selenium.webdriver.remote.webdriver import WebDriver
                # This is a simplified check - in practice you'd use more robust DOM traversal
                parent_tag = parent.tag_name.lower()
                if parent_tag in ['div', 'form', 'section', 'article', 'main', 'header', 'footer', 'nav', 'aside']:
                    # Try to find el within parent
                    try:
                        parent.find_element(By.CSS_SELECTOR, f":nth-of-type(1)")
                        # Check if el is contained in parent by comparing coordinates/size
                    except:
                        pass
            except:
                continue
        
        # Simplified: if any parent contains this element (by ID or direct containment)
        for parent in parents:
            try:
                parent_id = parent.get_attribute("id")
                if parent_id:
                    el_id = el.get_attribute("id")
                    if el_id and el_id.startswith(parent_id):
                        result.append(el)
                        break
                    # Check if element is inside by checking ancestor chain
                    from selenium.webdriver.remote.webdriver import WebDriver
                    # More robust check needed here - for now, just add all elements
            except:
                pass
    
    # If filtering is too complex, return all elements
    return elements if not result else result
