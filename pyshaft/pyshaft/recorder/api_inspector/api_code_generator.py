"""PyShaft API Inspector — Code generator that converts API workflow to PyShaft code."""

from __future__ import annotations

import json
import re

from pyshaft.recorder.api_inspector.api_models import (
    ApiAssertion,
    ApiExtraction,
    ApiFolder,
    ApiRequestStep,
    ApiWorkflow,
    AssertionType,
    AuthType,
    PipelineStep,
)

# ---------------------------------------------------------------------------
# Postman dynamic-var  →  Python expression
# ---------------------------------------------------------------------------
_DYNAMIC_VAR_TO_PYTHON: dict[str, str] = {
    "randomint":          "random.randint(0, 1_000)",
    "guid":               "str(uuid.uuid4())",
    "uuid":               "str(uuid.uuid4())",
    "timestamp":          "int(time.time())",
    "isotimestamp":       "time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())",
    "randomfloat":        "round(random.random(), 6)",
    "randomboolean":      "random.choice([True, False])",
    "randomalphanumeric": "random.choice(string.ascii_letters + string.digits)",
    "randomhexadecimal":  "'#{:06x}'.format(random.randint(0, 0xFFFFFF))",
    "randomcolor":        "random.choice(['red','blue','green','yellow','purple'])",
    "randomfirstname":    "random.choice(['Alice','Bob','Charlie','Diana','Eve'])",
    "randomlastname":     "random.choice(['Smith','Johnson','Williams','Brown','Jones'])",
    "randomfullname":     "random.choice(['Alice','Bob']) + ' ' + random.choice(['Smith','Johnson'])",
    "randomemail":        "random.choice(['alice','bob']) + str(random.randint(1,999)) + '@example.com'",
    "randomusername":     "'user' + str(random.randint(100, 9_999))",
    "randomword":         "random.choice(['apple','river','cloud','forest','stone'])",
    "randomwords":        "' '.join(random.choices(['apple','river','cloud','forest','stone'], k=3))",
    "randomloremword":    "random.choice(['lorem','ipsum','dolor','sit','amet'])",
    "randomurl":          "'https://www.' + random.choice(['apple','river','cloud']) + '.com'",
    "randomcity":         "random.choice(['Cairo','London','Paris','Tokyo','Berlin'])",
    "randomstreetaddress":"str(random.randint(1,999)) + ' ' + random.choice(['Apple','River','Cloud']) + ' St'",
    "randomcountry":      "random.choice(['Egypt','United Kingdom','France','Japan'])",
    "randomcountrycode":  "random.choice(['EG','GB','FR','JP','DE'])",
    "randomlatitude":     "round(random.uniform(-90, 90), 6)",
    "randomlongitude":    "round(random.uniform(-180, 180), 6)",
    "randomabbreviation": "''.join(random.choices(string.ascii_uppercase, k=random.randint(2, 4)))",
    "randomnoun":         "random.choice(['cat','bridge','fire','wave','mountain'])",
    "randomverb":         "random.choice(['run','jump','fly','swim','sing'])",
    "randomadjective":    "random.choice(['quick','lazy','bright','dark','cold'])",
}

_TEMPLATE_RE = re.compile(r"\{\{(\$?[a-zA-Z_][\w.\-]*)\}\}")


# ---------------------------------------------------------------------------
# Template string → Python code helpers
# ---------------------------------------------------------------------------

def _clean_var(name: str) -> str:
    """Convert Postman variable name to a valid Python identifier."""
    return name.replace("-", "_").replace(".", "_")


def _dyn_expr(key: str) -> str:
    """Return the Python expression for a $dynamic variable (key without $)."""
    return _DYNAMIC_VAR_TO_PYTHON.get(key.lower(), f"None  # unknown: ${key}")


def _str_to_py(value: str, use_pipeline: bool = True) -> str:
    """Convert a Postman template string to a Python source expression.

    "hello"              → '"hello"'
    "{{baseURL}}"        → 'get_value("baseURL")'  (or baseURL if use_pipeline=False)
    "{{$randomInt}}"     → 'random.randint(0, 1_000)'
    "hi {{$randomInt}}"  → '"hi " + str(random.randint(0, 1_000))'
    "{{a}}/{{b}}"        → 'str(get_value("a")) + "/" + str(get_value("b"))'
    
    Args:
        use_pipeline: If True, use get_value() for {{var}} (recommended)
    """
    matches = list(_TEMPLATE_RE.finditer(value))
    if not matches:
        return f'"{value}"'

    # Whole string is exactly one template → bare expression
    if len(matches) == 1 and matches[0].start() == 0 and matches[0].end() == len(value):
        var = matches[0].group(1)
        if var.startswith("$"):
            return _dyn_expr(var[1:])
        elif use_pipeline:
            return f'get_value("{_clean_var(var)}")'
        else:
            return _clean_var(var)

    # Mixed → string concatenation (works on all Python versions)
    parts: list[str] = []
    cursor = 0
    for m in matches:
        if m.start() > cursor:
            parts.append(f'"{value[cursor:m.start()]}"')
        var = m.group(1)
        if var.startswith("$"):
            expr = _dyn_expr(var[1:])
        elif use_pipeline:
            expr = f'get_value("{_clean_var(var)}")'
        else:
            expr = _clean_var(var)
        parts.append(f"str({expr})")
        cursor = m.end()
    if cursor < len(value):
        parts.append(f'"{value[cursor:]}"')
    return " + ".join(parts)


def _obj_to_py(obj, indent: str = "") -> str:
    """Recursively convert a JSON-parsed Python object to Python literal code.

    Key differences from json.dumps:
    - bool → True / False  (not true / false)
    - None → None          (not null)
    - str  → resolves Postman templates
    """
    inner = indent + "    "
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        rows = []
        items = list(obj.items())
        for i, (k, v) in enumerate(items):
            comma = "," if i < len(items) - 1 else ""
            rows.append(f'{inner}"{k}": {_obj_to_py(v, inner)}{comma}')
        return "{\n" + "\n".join(rows) + f"\n{indent}}}"
    if isinstance(obj, list):
        if not obj:
            return "[]"
        rows = []
        for i, v in enumerate(obj):
            comma = "," if i < len(obj) - 1 else ""
            rows.append(f"{inner}{_obj_to_py(v, inner)}{comma}")
        return "[\n" + "\n".join(rows) + f"\n{indent}]"
    if isinstance(obj, str):
        return _str_to_py(obj)
    if isinstance(obj, bool):
        return "True" if obj else "False"
    if obj is None:
        return "None"
    return repr(obj)


def _extra_imports(steps: list[ApiRequestStep]) -> list[str]:
    """Return sorted import lines needed by dynamic vars found in the steps."""
    needed: set[str] = set()

    def _scan(text: str) -> None:
        for m in _TEMPLATE_RE.finditer(text):
            var = m.group(1)
            if var.startswith("$"):
                expr = _DYNAMIC_VAR_TO_PYTHON.get(var[1:].lower(), "")
                if "random." in expr:  needed.add("import random")
                if "uuid."   in expr:  needed.add("import uuid")
                if "time."   in expr:  needed.add("import time")
                if "string." in expr:  needed.add("import string")

    for step in steps:
        _scan(step.url)
        _scan(step.payload or "")
        for v in step.headers.values():
            _scan(v)

    return sorted(needed)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_steps(items: list) -> list[ApiRequestStep]:
    steps: list[ApiRequestStep] = []
    for it in items:
        if isinstance(it, ApiRequestStep):
            steps.append(it)
        elif isinstance(it, ApiFolder):
            steps.extend(_collect_steps(it.items))
    return steps


def _has_assertions(steps: list[ApiRequestStep]) -> bool:
    return any(s.assertions or s.expected_status for s in steps)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_api_code(target, mode: str = "test") -> str:
    """Generate PyShaft code from an ApiWorkflow, ApiFolder, or ApiRequestStep."""
    if isinstance(target, ApiRequestStep):
        steps, name, base_url, variables = [target], target.name, "", {}
    elif isinstance(target, ApiFolder):
        steps, name, base_url, variables = _collect_steps(target.items), target.name, "", {}
    else:
        steps = target.all_steps
        name, base_url, variables = target.name, target.base_url, target.variables

    if not steps:
        return "# No API steps recorded yet\n"

    return _gen_pom(steps, name, base_url, variables) if mode == "pom" \
        else _gen_test(steps, name, base_url, variables)


# ---------------------------------------------------------------------------
# Test-script generator
# ---------------------------------------------------------------------------

def _gen_test(steps, name, base_url, variables) -> str:
    lines: list[str] = []

    # Dynamic imports first
    extra = _extra_imports(steps)
    if _has_assertions(steps):
        lines.append("import pytest")
    lines.extend(extra)
    lines.append("from pyshaft import api, get_value")
    lines.append("")
    lines.append("")

    test_name = "test_" + "".join(
        c if c.isalnum() else "_" for c in name.lower()
    ).strip("_") or "test_api"

    lines.append("@pytest.mark.pyshaft_api")
    lines.append(f"# @api.data_from_csv('data.csv')")
    lines.append(f"# @api.data_from_json('data.json')")
    lines.append(f"def {test_name}():")

    if base_url:
        lines.append(f'    # api.base_url("{base_url}")')
        lines.append("")

    if variables:
        for k, v in variables.items():
            lines.append(f'    {_clean_var(k)} = "{v}"')
        lines.append("")

    for i, step in enumerate(steps):
        lines.append(f"    # Step {i + 1}: {step.name}")
        lines.append("    (")
        lines.extend(_chain(step, base_url, indent="        "))
        lines.append("    )")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# POM generator
# ---------------------------------------------------------------------------

def _gen_pom(steps, name, base_url, variables) -> str:
    class_name = "".join(w.title() for w in name.split()) or "ApiCollection"
    extra = _extra_imports(steps)

    lines: list[str] = []
    lines.extend(extra)
    lines.append("from pyshaft import api")
    lines.append("")
    lines.append("")
    lines.append(f"class {class_name}:")
    lines.append('    """PyShaft API Page Object."""')
    lines.append("")

    if base_url:
        lines.append(f'    BASE_URL = "{base_url}"')
        lines.append("")

    for step in steps:
        method_name = "".join(c if c.isalnum() else "_" for c in step.name.lower()).strip("_") or "request"
        lines.append(f"    def {method_name}(self, **kwargs):")
        lines.append(f"        # {step.method} {step.url}")
        lines.append("        return (")
        lines.extend(_chain(step, base_url, indent="            ", is_pom=True))
        lines.append("        )")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Chain code builder
# ---------------------------------------------------------------------------

def _chain(step: ApiRequestStep, base_url: str = "", indent: str = "", is_pom: bool = False) -> list[str]:
    lines: list[str] = []

    if step.loop_variable:
        lines.append(f"{indent}for item in {step.loop_variable}:")
        indent += "    "

    lines.append(f"{indent}api.request()")

    # Method + URL
    method = step.method.value.lower()
    url = step.url
    if is_pom and base_url and url.startswith(base_url):
        url = url[len(base_url):]
        url_expr = _str_to_py(url)
        lines.append(f"{indent}.{method}(self.BASE_URL + {url_expr})")
    else:
        lines.append(f"{indent}.{method}({_str_to_py(url)})")

    # Headers
    for k, v in (step.headers or {}).items():
        lines.append(f"{indent}.header({_str_to_py(k)}, {_str_to_py(v)})")

    # Query Params
    for k, v in (step.query_params or {}).items():
        lines.append(f"{indent}.query({_str_to_py(k)}, {_str_to_py(v)})")

    # Auth
    if step.auth_type == AuthType.BEARER:
        lines.append(f'{indent}.header("Authorization", "Bearer " + str({step.auth_value}))')

    # Body
    if step.payload:
        # Check if entire body is a variable reference: {{my_body}}
        match = _TEMPLATE_RE.fullmatch(step.payload.strip())
        if match:
            var_name = match.group(1)
            lines.append(f"{indent}.body({_clean_var(var_name)})")
        else:
            try:
                obj = json.loads(step.payload)
                if step.loop_variable and step.loop_payload_key:
                    obj[step.loop_payload_key] = "__LOOP_ITEM__"
                py_body = _obj_to_py(obj, indent + "    ")
                # Restore loop item placeholder
                py_body = py_body.replace('"__LOOP_ITEM__"', "item")
                lines.append(f"{indent}.body({py_body})")
            except Exception:
                lines.append(f'{indent}.body({_str_to_py(step.payload)})')

    lines.append(f"{indent}.prettify()")

    if getattr(step, "retry_count", 0) > 0:
        lines.append(f"{indent}.retry({step.retry_count}, mode='{step.retry_mode}', backoff={step.retry_backoff})")

    # Assertions
    if step.expected_status:
        lines.append(f"{indent}.assert_status({step.expected_status})")

    for a in step.assertions:
        raw = str(a.expected)
        path = a.path
        
        # Smart Handling for Arrays (Loop/List Comp)
        # If path is data[*].id, we generate a list comprehension assertion
        is_array_iter = "[*]" in path
        
        # 1. Handle template variables or calculations
        fmt = re.sub(r"\{\{([^}]+)\}\}", r"\1", raw)
        is_calc = any(op in fmt for op in "+-*/")
        is_var = raw.startswith("{{") and raw.endswith("}}")
        
        if is_calc or is_var:
            final = fmt
        elif raw.lower() == "true": final = "True"
        elif raw.lower() == "false": final = "False"
        elif raw.lower() == "null": final = "None"
        else:
            try:
                if "." in raw:
                    float(raw); final = raw
                else:
                    int(raw); final = raw
            except ValueError:
                if raw.startswith("[") and " for " in raw and " in " in raw:
                    final = raw
                else:
                    final = f'"{raw}"'

        # Chained Method Mapping
        if is_array_iter:
             # data[*].id == 1  => .assert_json_path("data[*].id", [1, 1, 1]) 
             # For simpler usage we just pass the path and final
             lines.append(f'{indent}.assert_json_path("{path}", {final})')
        elif a.type == AssertionType.JSON_PATH_EQUALS:
            lines.append(f'{indent}.assert_json_path("{path}", {final})')
        elif a.type == AssertionType.JSON_PATH_CONTAINS:
            lines.append(f'{indent}.assert_json_contains("{path}", {final})')
        elif a.type == AssertionType.JSON_PATH_TYPE:
            type_val = a.expected if a.expected in ("int", "str", "float", "bool", "list", "dict") else f'"{a.expected}"'
            lines.append(f'{indent}.assert_json_type("{path}", {type_val})')
        elif a.type == AssertionType.JSON_PATH_DATE:
            lines.append(f'{indent}.assert_json_type("{path}", "date")')
        elif a.type == AssertionType.JSON_PATH_UUID:
            lines.append(f'{indent}.assert_json_type("{path}", "uuid")')
        elif a.type == AssertionType.JSON_SCHEMA:
            try:
                schema = json.dumps(json.loads(a.expected), indent=4).replace("\n", "\n" + indent + "    ")
                if a.path == "$":
                    lines.append(f"{indent}.assert_schema({schema})")
                else:
                    lines.append(f'{indent}.assert_schema({schema}, path="{path}")')
            except Exception:
                lines.append(f"{indent}.assert_schema({a.expected})")

    # Extractions
    for e in step.extractions:
        if e.json_path.endswith("[last]"):
            # Handle special [last] syntax for extraction
            real_path = e.json_path.replace("[last]", "[-1]")
            lines.append(f'{indent}.extract_json("{real_path}", "{e.variable_name}")')
        else:
            lines.append(f'{indent}.extract_json("{e.json_path}", "{e.variable_name}")')

    return lines
