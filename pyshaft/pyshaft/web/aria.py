"""PyShaft Aria Snapshots — Semantic structural assertions.

Provides methods to capture and assert against the ARIA tree of elements.
Inspired by Playwright's toMatchAriaSnapshot.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement

from pyshaft.core.action_runner import run_action

logger = logging.getLogger("pyshaft.web.aria")

# JavaScript to extract a simplified Aria Tree from an element
_ARIA_TREE_JS = r"""
function getAriaTree(root) {
    const roles_to_ignore = ['presentation', 'none', 'generic'];
    
    function isVisible(el) {
        if (!el) return false;
        if (el.getAttribute('aria-hidden') === 'true') return false;
        const style = window.getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    }

    function getRole(el) {
        const explicitRole = el.getAttribute('role');
        if (explicitRole) return explicitRole;
        
        const tag = el.tagName.toLowerCase();
        const type = el.getAttribute('type');
        
        if (tag === 'button') return 'button';
        if (tag === 'input') {
            if (['button', 'submit', 'reset'].includes(type)) return 'button';
            if (type === 'checkbox') return 'checkbox';
            if (type === 'radio') return 'radio';
            if (type === 'image') return 'button';
            return 'textbox';
        }
        if (tag === 'textarea') return 'textbox';
        if (tag === 'select') return 'combobox';
        if (tag === 'option') return 'option';
        if (tag === 'a' && el.getAttribute('href')) return 'link';
        if (/^h[1-6]$/.test(tag)) return 'heading';
        if (tag === 'table') return 'table';
        if (tag === 'ul' || tag === 'ol') return 'list';
        if (tag === 'li') return 'listitem';
        if (tag === 'form') return 'form';
        if (tag === 'nav') return 'navigation';
        if (tag === 'header') return 'banner';
        if (tag === 'footer') return 'contentinfo';
        if (tag === 'main') return 'main';
        if (tag === 'aside') return 'complementary';
        if (tag === 'section' && (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby'))) return 'region';
        
        return null;
    }

    function getName(el, role) {
        // 1. aria-label
        let name = el.getAttribute('aria-label');
        if (name) return name.trim();
        
        // 2. aria-labelledby
        const labelId = el.getAttribute('aria-labelledby');
        if (labelId) {
            const labelEl = document.getElementById(labelId);
            if (labelEl) return labelEl.innerText.trim();
        }

        // 3. label for (inputs)
        if (el.id) {
            const label = document.querySelector(`label[for="${el.id}"]`);
            if (label) return label.innerText.trim();
        }

        // 4. placeholder
        const placeholder = el.getAttribute('placeholder');
        if (placeholder) return placeholder.trim();
        
        // 5. title
        const title = el.getAttribute('title');
        if (title) return title.trim();

        // 6. alt (images)
        const alt = el.getAttribute('alt');
        if (alt) return alt.trim();

        // 7. inner text for specific roles
        const textRoles = ['button', 'link', 'heading', 'listitem', 'menuitem', 'tab', 'option'];
        if (textRoles.includes(role)) {
            // Only get direct text or flattened child text
            return el.innerText.trim().replace(/\s+/g, ' ');
        }
        
        // 8. For select, return the text of the selected option
        if (role === 'combobox' && el.tagName.toLowerCase() === 'select') {
            return el.options[el.selectedIndex] ? el.options[el.selectedIndex].text : '';
        }
        
        return '';
    }

    function buildNode(el) {
        if (!isVisible(el)) return null;

        const role = getRole(el);
        const name = role ? getName(el, role) : '';
        
        const children = [];
        // Note: For select, children are options
        for (const child of el.children) {
            const node = buildNode(child);
            if (node) {
                if (Array.isArray(node)) children.push(...node);
                else children.push(node);
            }
        }

        if (!role || roles_to_ignore.includes(role)) {
            // Container node — flatten if possible
            return children.length > 0 ? children : null;
        }

        const node = { role };
        if (name) node.name = name;
        
        if (role === 'heading') {
            const levelMatch = el.tagName.match(/H(\d)/i);
            if (levelMatch) node.level = parseInt(levelMatch[1], 10);
        }

        if (role === 'link' && el.getAttribute('href')) {
            node.url = el.getAttribute('href');
        }

        if (['textbox', 'combobox', 'searchbox', 'option'].includes(role) && el.value) {
            node.value = el.value;
        }
        
        if (children.length > 0) node.children = children;
        return node;
    }

    const tree = buildNode(root);
    return Array.isArray(tree) ? tree[0] : tree;
}
return getAriaTree(arguments[0]);
"""

def get_aria_tree(locator: str) -> dict[str, Any]:
    """Capture the semantic Aria Tree for an element and its children."""
    def _capture(driver: WebDriver) -> dict[str, Any]:
        from pyshaft.core.locator import DualLocator
        element = DualLocator.resolve(driver, locator)
        return driver.execute_script(_ARIA_TREE_JS, element)
    
    from pyshaft.core.action_runner import run_driver_action
    return run_driver_action("get_aria_tree", locator, _capture)

def tree_to_yaml(node: dict[str, Any], indent: int = 0) -> str:
    """Convert an Aria Tree dictionary to a YAML-like string."""
    if not node: return ""
    
    line = "  " * indent + f"- {node['role']}"
    if "name" in node:
        line += f' "{node["name"]}"'
    if "level" in node:
        line += f" [level={node['level']}]"
    
    lines = [line]
    
    # Attributes
    attr_indent = "  " * (indent + 1)
    if "url" in node:
        lines.append(f"{attr_indent}/url: {node['url']}")
    if "value" in node:
        lines.append(f"{attr_indent}/value: {node['value']}")

    if "children" in node:
        for child in node["children"]:
            lines.append(tree_to_yaml(child, indent + 1))
            
    return "\n".join(lines)

def assert_aria_snapshot(locator: str, expected_yaml: str) -> None:
    """Assert that an element's Aria Tree matches the expected YAML-like structure."""
    tree = get_aria_tree(locator)
    actual_yaml = tree_to_yaml(tree)
    
    actual_lines = [l for l in actual_yaml.splitlines() if l.strip()]
    expected_lines = [l for l in expected_yaml.splitlines() if l.strip()]
    
    if len(actual_lines) != len(expected_lines):
        raise AssertionError(
            f"Aria Snapshot mismatch for {locator!r}: Line count differs.\n"
            f"EXPECTED ({len(expected_lines)} lines):\n{expected_yaml.strip()}\n"
            f"ACTUAL ({len(actual_lines)} lines):\n{actual_yaml.strip()}"
        )

    # Line parser: matches optional indent, then "- role", then optional "name" or /regex/, then optional [level=N]
    # Example: '  - heading /Welcome/ [level=1]'
    # Groups: 1=indent, 2=role, 3=name_or_regex, 4=level
    line_pattern = re.compile(r'^(\s*)-\s+([a-zA-Z0-9_]+)(?:\s+("[^"]*"|/[^/]*/))?(?:\s+\[level=(\d+)\])?.*$')

    for i, (act, exp) in enumerate(zip(actual_lines, expected_lines)):
        m_act = line_pattern.match(act)
        m_exp = line_pattern.match(exp)
        
        if not m_act or not m_exp:
            # Fallback to direct comparison if line doesn't match standard pattern (e.g. attributes)
            if _normalize_yaml(act) != _normalize_yaml(exp):
                raise AssertionError(
                    f"Aria Snapshot mismatch at line {i+1}:\n"
                    f"Expected: {exp.strip()!r}\n"
                    f"Actual:   {act.strip()!r}"
                )
            continue

        # 1. Compare Indentation
        if len(m_act.group(1)) != len(m_exp.group(1)):
            raise AssertionError(
                f"Aria Snapshot mismatch at line {i+1}: Indentation differs.\n"
                f"Expected: {exp!r}\n"
                f"Actual:   {act!r}"
            )
            
        # 2. Compare Role
        if m_act.group(2) != m_exp.group(2):
            raise AssertionError(
                f"Aria Snapshot mismatch at line {i+1}: Role mismatch.\n"
                f"Expected role: {m_exp.group(2)!r}\n"
                f"Actual role:   {m_act.group(2)!r}"
            )
            
        # 3. Compare Name / Regex
        exp_val = m_exp.group(3)
        act_val = m_act.group(3) or ""
        
        if exp_val:
            if exp_val.startswith('/'):
                # Regex match
                pattern = exp_val[1:-1]
                # Actual value might be wrapped in quotes
                clean_act = act_val.strip('"')
                if not re.search(pattern, clean_act):
                    raise AssertionError(
                        f"Aria Snapshot mismatch at line {i+1}: Regex mismatch.\n"
                        f"Pattern: {pattern!r}\n"
                        f"Actual:  {clean_act!r}"
                    )
            else:
                # Direct string match (normalized quotes)
                clean_exp = exp_val.strip('"')
                clean_act = act_val.strip('"')
                if clean_exp != clean_act:
                    raise AssertionError(
                        f"Aria Snapshot mismatch at line {i+1}: Name mismatch.\n"
                        f"Expected: {clean_exp!r}\n"
                        f"Actual:   {clean_act!r}"
                    )

        # 4. Compare Level
        if m_exp.group(4) and m_act.group(4) != m_exp.group(4):
            raise AssertionError(
                f"Aria Snapshot mismatch at line {i+1}: Level mismatch.\n"
                f"Expected level: {m_exp.group(4)}\n"
                f"Actual level:   {m_act.group(4)}"
            )

def _normalize_yaml(yaml_str: str) -> str:
    """Clean up YAML for easier comparison while PRESERVING indentation."""
    import re
    # 1. Remove empty lines
    lines = [line for line in yaml_str.splitlines() if line.strip()]
    # 2. Normalize spacing within each line but keep relative leading spaces
    normalized = []
    for line in lines:
        leading_spaces = len(line) - len(line.lstrip())
        content = line.strip()
        # Collapse internal multiple spaces
        content = re.sub(r'\s+', ' ', content)
        normalized.append(" " * leading_spaces + content)
        
    # 3. Standardize quotes and join
    res = "\n".join(normalized).replace("'", '"')
    return res.strip()
