"""PyShaft Recorder — Code generator that converts recorded steps to PyShaft test code."""

from __future__ import annotations

import json
from typing import Any

from pyshaft.recorder.models import RecordedStep, RecordingSession


# Locator types that need specific imports
_LOCATOR_IMPORTS = {
    "role": "role", "text": "text", "label": "label",
    "placeholder": "placeholder", "testid": "testid",
    "id": "id_", "class": "cls", "css": "css_",
    "xpath": "xpath", "tag": "tag", "attr": "attr", "any": "any_",
}

# HTML element constants that need imports
_ELEMENT_IMPORTS = {
    "button", "textbox", "input", "checkbox", "radio", "link",
    "menu", "menuitem", "dialog", "modal", "form", "heading",
    "alert", "spinner", "image", "listbox", "option", "combobox",
    "password", "email", "submit",
}

# Elements that use trailing underscore in Python
_ELEMENT_UNDERSCORE = {"input": "input_"}


def generate_code(
    session: RecordingSession,
    mode: str = "chain",
    test_name: str = "",
) -> str:
    """Generate PyShaft test code from a recording session.

    Args:
        session: The recording session with steps.
        mode: "flat" for one-action-per-line, "chain" for fluent chaining.
        test_name: Test function name (auto-generated from session name if empty).

    Returns:
        Complete Python test file as a string if mode is 'flat' or 'chain', 
        or a dict of strings for 'pom' mode (test.py, page.py, data.py).
    """
    if mode == "pom":
        return _generate_pom_mode(session, test_name)

    if not session.steps:
        return "# No steps recorded yet\n"

    if not test_name:
        # Convert session name to snake_case
        test_name = "test_" + "".join(
            c if c.isalnum() else "_" for c in session.name.lower()
        ).strip("_")

    # Collect needed imports
    imports = _collect_imports(session.steps)

    lines: list[str] = []

    # Header
    lines.append("import pytest")
    lines.append(imports)
    lines.append("")
    lines.append("")

    # Test function
    lines.append("@pytest.mark.pyshaft_web")
    lines.append(f"def {test_name}():")

    if mode == "chain":
        lines.extend(_generate_chain_mode(session.steps))
    else:
        lines.extend(_generate_flat_mode(session.steps))

    lines.append("")
    return "\n".join(lines)


def _collect_imports(steps: list[RecordedStep]) -> str:
    """Collect all required imports from the steps."""
    # Collect locator names using set comprehension
    locator_names = {
        _LOCATOR_IMPORTS[st] 
        for s in steps 
        for st in [s.locator_type, *(s.inside[0] if s.inside else []), *s.filters.keys()]
        if st in _LOCATOR_IMPORTS
    }

    # Collect element names using set comprehension
    # Check locator_value and inside[1]
    element_names = {
        _ELEMENT_UNDERSCORE.get(val, val)
        for s in steps
        for val in [s.locator_value, *(s.inside[1] if s.inside else [])]
        if val in _ELEMENT_IMPORTS
    }

    all_imports = sorted(locator_names | element_names)
    import_line = f", {', '.join(all_imports)}" if all_imports else ""
    return f"from pyshaft import web as w{import_line}"


def _generate_flat_mode(steps: list[RecordedStep]) -> list[str]:
    """Generate code with each action on its own line."""
    return [f"    {_step_to_code(step)}" for step in steps]


def _generate_chain_mode(steps: list[RecordedStep]) -> list[str]:
    """Generate code with fluent chaining where possible."""
    if not steps:
        return []

    lines: list[str] = []
    chain: list[RecordedStep] = []

    def flush_chain():
        if not chain:
            return
        
        if len(chain) == 1:
            lines.append(f"    {_step_to_code(chain[0])}")
        else:
            # Check if we can fit the whole chain on one line
            # (Simple heuristic: 2 steps and no multiline args)
            first_code = _step_to_code(chain[0])
            rest_codes = [_step_to_chain_code(s) for s in chain[1:]]
            
            is_multiline = any("\n" in c for c in [first_code] + rest_codes)
            total_len = len(first_code) + sum(len(c) + 1 for c in rest_codes)
            
            if not is_multiline and total_len < 100:
                full_line = first_code + "".join(f".{c}" for c in rest_codes)
                lines.append(f"    {full_line}")
            else:
                # Standard multiline chain
                lines.append(f"    ({first_code}")
                for i, code in enumerate(rest_codes):
                    suffix = ")" if i == len(rest_codes) - 1 else ""
                    # Handle internal newlines (like Aria Snapshots)
                    if "\n" in code:
                        # Indent sub-lines of the code itself
                        indented_code = code.replace("\n", "\n     ")
                        lines.append(f"     .{indented_code}{suffix}")
                    else:
                        lines.append(f"     .{code}{suffix}")
        chain.clear()

    for step in steps:
        # Navigation steps break the chain
        if step.action in ("open_url", "go_back", "go_forward", "refresh"):
            flush_chain()
            lines.append(f"    {_step_to_code(step)}")
        else:
            chain.append(step)

    flush_chain()
    return lines

def _generate_pom_mode(session: RecordingSession, test_name: str) -> dict[str, str]:
    """Generate code split into test.py, page.py, and data.py."""
    if not session.steps:
        return {
            "test.py": "# No steps recorded yet\n",
            "page.py": "# Page object empty\n",
            "data.py": "# Data empty\n",
        }

    if not test_name:
        test_name = "test_" + "".join(
            c if c.isalnum() else "_" for c in session.name.lower()
        ).strip("_")

    page_vars: dict[str, str] = {}
    data_vars: dict[str, str] = {}
    
    # We will mutate a copy of steps for the test output
    import copy
    steps_copy = copy.deepcopy(session.steps)

    page_counter = 1
    data_counter = 1

    for step in steps_copy:
        # Extract locator string to page.py if it's not a native element
        if step.locator_value and step.locator_value not in _ELEMENT_IMPORTS:
            # Check if it's URL
            if step.action == "open_url":
                var_name = f"url_{data_counter}"
                data_vars[var_name] = step.locator_value
                step.locator_value = f"data.{var_name}"
                data_counter += 1
            else:
                ltype = step.locator_type or "any"
                var_name = f"{ltype}_locator_{page_counter}"
                page_vars[var_name] = step.locator_value
                step.locator_value = f"page.{var_name}"
                page_counter += 1

        # Extract typed text to data.py
        if step.typed_text:
            var_name = f"text_{data_counter}"
            data_vars[var_name] = step.typed_text
            step.typed_text = f"data.{var_name}"
            data_counter += 1

        # Extract assertion expected to data.py
        if step.assert_expected:
            var_name = f"expected_{data_counter}"
            data_vars[var_name] = step.assert_expected
            step.assert_expected = f"data.{var_name}"
            data_counter += 1

        # Extract inside
        if step.inside:
            itype, ivalue = step.inside
            if ivalue not in _ELEMENT_IMPORTS:
                var_name = f"{itype}_locator_{page_counter}"
                page_vars[var_name] = ivalue
                step.inside = (itype, f"page.{var_name}")
                page_counter += 1
                
        # Extract filters containing strings
        if step.filters:
            for k, v in step.filters.items():
                if isinstance(v, str) and v and k != "force":
                    var_name = f"filter_{data_counter}"
                    data_vars[var_name] = v
                    step.filters[k] = f"data.{var_name}"
                    data_counter += 1

    # Generate page.py
    page_lines = ["class Page:", "    pass", ""]
    page_lines.append("page = Page()")
    for k, v in page_vars.items():
        page_lines.append(f'page.{k} = "{v}"')
    page_code = "\n".join(page_lines) + "\n"
    if not page_vars:
        page_code = "# No custom locators used.\n"

    # Generate data.py
    data_lines = ["class Data:", "    pass", ""]
    data_lines.append("data = Data()")
    for k, v in data_vars.items():
        data_lines.append(f'data.{k} = "{v}"')
    data_code = "\n".join(data_lines) + "\n"
    if not data_vars:
        data_code = "# No custom string data used.\n"

    # Generate test.py
    imports = _collect_imports(steps_copy)
    test_lines = []
    test_lines.append("import pytest")
    test_lines.append(imports)
    if page_vars:
        test_lines.append("from page import page")
    if data_vars:
        test_lines.append("from data import data")
    test_lines.append("")
    test_lines.append("")
    test_lines.append("@pytest.mark.pyshaft_web")
    test_lines.append(f"def {test_name}():")
    
    # We use chain mode for the test body
    test_lines.extend(_generate_chain_mode(steps_copy))
    test_lines.append("")
    
    test_code = "\n".join(test_lines)

    return {
        "test.py": test_code,
        "page.py": page_code,
        "data.py": data_code,
    }


def _step_to_code(step: RecordedStep) -> str:
    """Convert a single step to a complete PyShaft code line."""
    if step.action == "open_url":
        return f'w.open_url("{step.url or step.locator_value}")'

    if step.action == "go_back":
        return "w.go_back()"

    if step.action == "go_forward":
        return "w.go_forward()"

    if step.action == "refresh":
        return "w.refresh()"

    if step.action == "accept_alert":
        return "w.accept_alert()"

    if step.action == "dismiss_alert":
        return "w.dismiss_alert()"

    if step.action == "get_alert_text":
        return "w.get_alert_text()"

    if step.action == "switch_to_default":
        return "w.switch_to_default()"

    # ── Data extraction steps ──────────────────────────────────────────────
    if step.action in ("get_text", "get_value", "get_selected_option",
                        "get_text_as_int", "get_text_as_float", "get_text_as_str"):
        loc_type = step.locator_type or ""
        loc_value = step.locator_value or ""
        py_type = _LOCATOR_IMPORTS.get(loc_type, f'"{loc_type}"') if loc_type else ""
        py_value = _format_value(loc_value)

        # Determine the base action (strip cast suffix)
        base_action = step.action
        if step.action.startswith("get_text_as_"):
            base_action = "get_text"

        # Build locator args
        if py_type and py_value:
            call = f"w.{base_action}({py_type}, {py_value})"
        elif py_value:
            call = f"w.{base_action}({py_value})"
        else:
            call = f"w.{base_action}()"

        # Add modifiers
        call += _build_modifiers(step)

        # Apply cast wrapper
        if step.cast_type == "int":
            call = f"int({call})"
        elif step.cast_type == "float":
            call = f"float({call})"
        elif step.cast_type == "str":
            call = f"str({call})"

        # Assign to variable
        var = step.extract_variable or "_result"
        return f"{var} = {call}"

    # ── Data type assertion ────────────────────────────────────────────────
    if step.action == "assert_data_type" and step.assert_data_type_name:
        loc_type = step.locator_type or ""
        loc_value = step.locator_value or ""
        py_type = _LOCATOR_IMPORTS.get(loc_type, f'"{loc_type}"') if loc_type else ""
        py_value = _format_value(loc_value)

        if py_type and py_value:
            return f'w.assert_data_type("{step.assert_data_type_name}", {py_type}, {py_value})'
        return f'w.assert_data_type("{step.assert_data_type_name}")'

    # Build the base call
    base = _build_action_call(step)
    modifiers = _build_modifiers(step)

    return f"w.{base}{modifiers}"


def _step_to_chain_code(step: RecordedStep) -> str:
    """Convert a step to chainable code (without 'w.' prefix)."""
    base = _build_action_call(step)
    modifiers = _build_modifiers(step)
    return f"{base}{modifiers}"


def _build_action_call(step: RecordedStep) -> str:
    """Build the action call portion: click(role, button) or type("text", id, "field")."""
    action = step.action

    # Locator arguments
    loc_type = step.locator_type or ""
    loc_value = step.locator_value or ""

    # Python constant names
    py_type = _LOCATOR_IMPORTS.get(loc_type, f'"{loc_type}"') if loc_type else ""
    py_value = _format_value(loc_value)

    # Handle modifier as a property chain: w.click.contain(text="Submit")
    if step.modifier and step.modifier in ("exact", "contain", "starts"):
        if loc_type and loc_value:
            # Map kwarg key
            kwarg_key = _LOCATOR_IMPORTS.get(loc_type, loc_type)
            if kwarg_key == "cls":
                kwarg_key = "class_"

            # For actions with required text argument (type, select) or assertion strings
            if action in ("type", "pick_date", "upload_file") and step.typed_text is not None:
                txt = _format_string(step.typed_text)
                return f'{action}({txt}).{step.modifier}({kwarg_key}={py_value})'

            if action in ("select", "select_dynamic") and step.typed_text:
                txt = _format_string(step.typed_text)
                return f'{action}({txt}).{step.modifier}({kwarg_key}={py_value})'

            if action.startswith("assert") and step.assert_expected:
                if action not in ("assert_title", "assert_url", "assert_contain_title", "assert_contain_url", "assert_snapshot"):
                    txt = _format_string(step.assert_expected)
                    return f'{action}({txt}).{step.modifier}({kwarg_key}={py_value})'
                if action == "assert_snapshot":
                    txt = _format_string(step.assert_expected)
                    return f'{action}({txt})'

            # Default modifier chain
            return f'{action}.{step.modifier}({kwarg_key}={py_value})'

    # Normal actions without property chain modifiers
    
    # Type / Input action: type("text", locator_type, value)
    if action in ("type", "pick_date", "upload_file") and step.typed_text is not None:
        text_arg = step.typed_text if step.typed_text.startswith("data.") else _format_string(step.typed_text)
        if py_type and py_value:
            return f'{action}({text_arg}, {py_type}, {py_value})'
        elif py_value:
            return f'{action}({text_arg}, {py_value})'
        else:
            return f'{action}({text_arg})'

    # Assert with expected value
    if action.startswith("assert") and step.assert_expected:
        if action == "assert_aria_snapshot":
            expected = _format_string(step.assert_expected, force_single_line=True)
        else:
            expected = step.assert_expected if step.assert_expected.startswith("data.") else _format_string(step.assert_expected)
            
        if action in ("assert_title", "assert_url", "assert_contain_title", "assert_contain_url"):
            return f'{action}({expected})'
        if py_type and py_value:
            return f'{action}({expected}, {py_type}, {py_value})'
        return f'{action}({expected})'

    # Select action: select("option", locator_type, value)
    if action in ("select", "select_dynamic") and step.typed_text:
        text_arg = step.typed_text if step.typed_text.startswith("data.") else _format_string(step.typed_text)
        if py_type and py_value:
            return f'{action}({text_arg}, {py_type}, {py_value})'
        return f'{action}({text_arg})'

    # Standard action: click(locator_type, value)
    if action == "wait_until_disappears":
        action = "wait_until_disappears" # logic check
        
    if action == "force_click":
        action = "force_click"

    if action == "remove":
        action = "remove_element"

    if py_type and py_value:
        return f'{action}({py_type}, {py_value})'
    elif py_value:
        return f'{action}({py_value})'
    else:
        return f'{action}()'


def _build_modifiers(step: RecordedStep) -> str:
    """Build the modifier chain: .filter().inside().nth()."""
    parts: list[str] = []

    # Filters using list comprehension
    if step.filters:
        args = [f'{"class_" if k == "class" else k}={_format_string(v)}' for k, v in step.filters.items()]
        parts.append(f'.filter({", ".join(args)})')

    # Inside
    if step.inside:
        inside_type, inside_value = step.inside
        py_type = _LOCATOR_IMPORTS.get(inside_type, f'"{inside_type}"')
        parts.append(f'.inside({py_type}, {_format_string(inside_value)})')

    # Index
    if step.index is not None:
        parts.append(f'.nth({step.index})')

    return "".join(parts)


def _format_string(text: str, force_single_line: bool = False) -> str:
    """Safely format a string for Python code, escaping quotes and handling newlines."""
    if not text: return '""'
    import json
    if force_single_line:
        # json.dumps handles both " and \n escaping perfectly
        return json.dumps(text.strip())
    
    # If it has newlines and we allow multiline, use triple quotes (not used currently per user request)
    # but here we follow user's "one line" request for aria snapshots
    return json.dumps(text.strip())

def _format_value(value: str) -> str:
    """Format a locator value — element constants stay bare, others getting quotes unless from POM."""
    if value in _ELEMENT_IMPORTS:
        return _ELEMENT_UNDERSCORE.get(value, value)
    if value.startswith("page.") or value.startswith("data."):
        return value
    return _format_string(value)
