"""PyShaft API Inspector — Code generator that converts API workflow to PyShaft code."""

from __future__ import annotations

import json
from pyshaft.recorder.api_inspector.api_models import (
    ApiAssertion,
    ApiExtraction,
    ApiRequestStep,
    ApiWorkflow,
    AssertionType,
    AuthType,
    HttpMethod,
    PipelineStep,
)


def generate_api_code(workflow: ApiWorkflow, mode: str = "test") -> str:
    """Generate PyShaft API test code from a workflow.

    Args:
        workflow: The API workflow to convert.
        mode: "test" for flat script, "pom" for class-based.

    Returns:
        Complete Python code as a string.
    """
    steps = workflow.all_steps
    if not steps:
        return "# No API steps recorded yet\n"

    if mode == "pom":
        return _generate_pom_code(workflow)
    else:
        return _generate_test_code(workflow)


def _generate_test_code(workflow: ApiWorkflow) -> str:
    """Generate flat pytest-style script."""
    steps = workflow.all_steps
    lines: list[str] = []

    # Imports
    lines.append("import pytest")
    lines.append("from pyshaft import api")
    lines.append("")
    lines.append("")

    # Test function
    test_name = "test_" + "".join(
        c if c.isalnum() else "_" for c in workflow.name.lower()
    ).strip("_")

    lines.append("@pytest.mark.pyshaft_api")
    lines.append(f"def {test_name}():")

    # Base URL (optional global)
    if workflow.base_url:
        lines.append(f'    # api.base_url("{workflow.base_url}")')
        lines.append("")

    # Global Variables
    if workflow.variables:
        for var_name, var_value in workflow.variables.items():
            lines.append(f'    {var_name} = "{var_value}"')
        lines.append("")

    # Steps
    for i, step in enumerate(steps):
        lines.append(f"    # Step {i + 1}: {step.name}")
        lines.append("    (")
        step_lines = _generate_chain_code(step, workflow, indent="        ")
        lines.extend(step_lines)
        lines.append("    )")
        lines.append("")

    return "\n".join(lines)


def _generate_pom_code(workflow: ApiWorkflow) -> str:
    """Generate Page Object Model (Class-based) code."""
    steps = workflow.all_steps
    class_name = "".join(c.title() for c in workflow.name.split()).replace(" ", "")
    if not class_name: class_name = "ApiCollection"

    lines: list[str] = []
    lines.append("from pyshaft import api")
    lines.append("")
    lines.append("")
    lines.append(f"class {class_name}:")
    lines.append('    """PyShaft API Page Object."""')
    lines.append("")
    
    if workflow.base_url:
        lines.append(f'    BASE_URL = "{workflow.base_url}"')
        lines.append("")

    for step in steps:
        method_name = "".join(c if c.isalnum() else "_" for c in step.name.lower()).strip("_")
        lines.append(f"    def {method_name}(self, **kwargs):")
        lines.append(f"        # {step.method} {step.url}")
        lines.append("        return (")
        step_lines = _generate_chain_code(step, workflow, indent="            ", is_pom=True)
        lines.extend(step_lines)
        lines.append("        )")
        lines.append("")

    return "\n".join(lines)


def _generate_chain_code(step: ApiRequestStep, workflow: ApiWorkflow, indent: str, is_pom: bool = False) -> list[str]:
    """Generate the fluent chain lines with loop and variable support."""
    lines: list[str] = []
    
    # Handle Loop
    if step.loop_variable:
        lines.append(f"{indent}for item in {step.loop_variable}:")
        indent += "    "

    # 1. Start with request()
    lines.append(f"{indent}api.request()")
    
    # 2. Method and URL
    method = step.method.value.lower()
    url = step.url
    if is_pom and workflow.base_url and url.startswith(workflow.base_url):
        url = url[len(workflow.base_url):]
        lines.append(f'{indent}.{method}(self.BASE_URL + "{url}")')
    else:
        lines.append(f'{indent}.{method}("{url}")')

    # 3. Headers
    if step.headers:
        for k, v in step.headers.items():
            lines.append(f'{indent}.header("{k}", "{v}")')

    # 4. Auth
    if step.auth_type == AuthType.BEARER:
        lines.append(f'{indent}.header("Authorization", f"Bearer {{{step.auth_value}}}")')

    # 5. Body with Loop logic
    if step.payload:
        try:
            obj = json.loads(step.payload)
            # If looping, replace the target key with 'item'
            if step.loop_variable and step.loop_payload_key:
                obj[step.loop_payload_key] = "__PYSHAFT_LOOP_ITEM__"
            
            payload_str = json.dumps(obj, indent=4).replace("\n", "\n" + indent + "    ")
            payload_str = payload_str.replace('"__PYSHAFT_LOOP_ITEM__"', "item")
            lines.append(f'{indent}.body({payload_str})')
        except:
            lines.append(f'{indent}.body("""{step.payload}""")')

    # 6. Prettify
    lines.append(f"{indent}.prettify()")

    # 6b. Retry
    if getattr(step, "retry_count", 0) > 0:
        lines.append(f"{indent}.retry({step.retry_count}, mode='{step.retry_mode}', backoff={step.retry_backoff})")

    # 7. Assertions
    if step.expected_status:
        lines.append(f"{indent}.assert_status({step.expected_status})")
    
    for a in step.assertions:
        # Smart formatting for expected value (handle variables and calculations)
        raw_expected = a.expected
        
        # 1. Convert {{var}} to just var
        import re
        formatted_expected = re.sub(r"\{\{([^}]+)\}\}", r"\1", raw_expected)
        
        # 2. Decide if we need quotes
        is_calc = any(op in formatted_expected for op in ("+", "-", "*", "/"))
        is_var = raw_expected.startswith("{{") and raw_expected.endswith("}}")
        
        if is_calc or is_var:
            final_val = formatted_expected
        else:
            try:
                # If it's a number, no quotes
                float(formatted_expected)
                final_val = formatted_expected
            except:
                # String literal
                final_val = f'"{formatted_expected}"'
        
        if a.type == AssertionType.JSON_PATH_EQUALS:
            lines.append(f'{indent}.assert_json_path("{a.path}", {final_val})')
        elif a.type == AssertionType.JSON_PATH_CONTAINS:
            lines.append(f'{indent}.assert_json_contains("{a.path}", {final_val})')
        elif a.type == AssertionType.JSON_PATH_TYPE:
            lines.append(f'{indent}.assert_json_type("{a.path}", "{a.expected}")')

    # 8. Extractions
    for e in step.extractions:
        lines.append(f'{indent}.extract_json("{e.json_path}", "{e.variable_name}")')

    return lines
