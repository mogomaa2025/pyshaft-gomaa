"""PyShaft API response wrapper — fluent assertions and extraction."""

from __future__ import annotations

import json
from typing import Any

import httpx

from pyshaft.api.store import store_data


class ApiResponse:
    """Fluent wrapper for httpx.Response."""

    def __init__(self, response: httpx.Response):
        self._response = response
        self.status_code = response.status_code
        self.text = response.text
        try:
            self.json_data = response.json()
        except Exception:
            self.json_data = None

    def assert_status(self, expected: int) -> ApiResponse:
        """Assert that the response status code matches expected."""
        if self.status_code != expected:
            raise AssertionError(
                f"API Status Mismatch\n"
                f"Expected: {expected}\n"
                f"Actual:   {self.status_code}\n"
                f"Body:     {self.text[:500]}"
            )
        return self

    def assert_json(self, path: str, expected: Any) -> ApiResponse:
        """Assert that a JSON value at a given path matches expected.
        
        Path uses dot notation (e.g., 'data.user.id') or brackets (e.g., 'items[0].id').
        """
        actual = self._get_by_path(path)
        if actual != expected:
            raise AssertionError(
                f"API JSON Mismatch at {path!r}\n"
                f"Expected: {expected!r}\n"
                f"Actual:   {actual!r}"
            )
        return self

    def assert_json_contains(self, path: str, expected: Any) -> ApiResponse:
        """Assert that a JSON collection at path contains the expected item.
        Supports 'Simple English' syntax.
        """
        return self.assert_json_path(path).should_contain(expected)

    def assert_json_type(self, path: str, expected_type: str) -> ApiResponse:
        """Assert that a JSON value at path is of a specific type.
        Supports 'Simple English' syntax.
        """
        return self.assert_json_path(path).should_be_type(expected_type)

    def assert_json_in_array(self, path: str, criteria: dict) -> ApiResponse:
        """Assert that an array at path contains an object matching the criteria."""
        items = self._get_by_path(path)
        if not isinstance(items, list):
            raise TypeError(f"Path {path!r} is not an array")
        
        found = any(
            isinstance(item, dict) and all(item.get(k) == v for k, v in criteria.items())
            for item in items
        )
        
        if not found:
            raise AssertionError(f"No object in {path!r} matches criteria {criteria!r}")
        return self

    def assert_schema(self, schema: dict, path: str = "$") -> ApiResponse:
        """Assert that a JSON value at path matches a JSON Schema."""
        try:
            import jsonschema
        except ImportError:
            raise ImportError("jsonschema is required for assert_schema. Install with: pip install jsonschema")
            
        actual = self._get_by_path(path) if path != "$" else self.json_data
        try:
            jsonschema.validate(instance=actual, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            raise AssertionError(f"Schema validation failed at path {path!r}: {e.message}")
        return self

    def assert_partial_schema(self, schema: dict, ignore_keys: list[str], path: str = "$") -> ApiResponse:
        """Assert that a JSON value at path matches a schema, ignoring specific keys.
        
        Args:
            schema: The JSON Schema to validate against.
            ignore_keys: List of keys to remove from the actual data before validation.
            path: Optional JSONPath to the data to validate.
        """
        import copy
        actual = self._get_by_path(path) if path != "$" else self.json_data
        
        # Deep copy to avoid mutating the original response data
        data_to_validate = copy.deepcopy(actual)
        
        def _remove_keys(obj, keys):
            if isinstance(obj, dict):
                for k in list(obj.keys()):
                    if k in keys:
                        del obj[k]
                    else:
                        _remove_keys(obj[k], keys)
            elif isinstance(obj, list):
                for item in obj:
                    _remove_keys(item, keys)

        _remove_keys(data_to_validate, ignore_keys)
        
        try:
            import jsonschema
            jsonschema.validate(instance=data_to_validate, schema=schema)
        except ImportError:
            raise ImportError("jsonschema is required for schema validation. Install with: pip install jsonschema")
        except jsonschema.exceptions.ValidationError as e:
            raise AssertionError(f"Partial schema validation failed at path {path!r} (ignored keys: {ignore_keys}): {e.message}")
            
        return self

    def extract_json(self, path: str, key: str) -> ApiResponse:
        """Extract a JSON value at path and store it in global memory.
        Supports 'Simple English' syntax.
        """
        val = self.assert_json_path(path)._matches
        if val:
            store_data(key, val[0])
        return self

    def save(self, path: str, key: str) -> ApiResponse:
        """Alias for extract_json."""
        return self.extract_json(path, key)

    def for_each(self, path: str, callback: Any) -> ApiResponse:
        """Execute a callback function for each item in a JSON array at path.
        Supports 'Simple English' syntax.
        """
        matches = self.assert_json_path(path)._matches
        if not matches or not isinstance(matches[0], list):
            raise TypeError(f"Path {path!r} is not an array (found {type(matches[0]).__name__ if matches else 'nothing'})")
        
        items = matches[0]
        for index, item in enumerate(items):
            try:
                callback(item)
            except Exception as e:
                raise AssertionError(f"Error during for_each on index {index} of {path!r}: {e}")
        return self

    def for_each_key(self, path: str, callback: Any) -> ApiResponse:
        """Execute a callback function for each key in a JSON object at path.
        Supports 'Simple English' syntax.
        """
        matches = self.assert_json_path(path)._matches
        if not matches or not isinstance(matches[0], dict):
            raise TypeError(f"Path {path!r} is not an object")
        
        obj = matches[0]
        for key in obj.keys():
            try:
                callback(key)
            except Exception as e:
                raise AssertionError(f"Error during for_each_key on key {key!r} of {path!r}: {e}")
        return self

    def map(self, path: str, field: str) -> list[Any]:
        """Extract a specific field from every object in an array at path.
        Supports 'Simple English' syntax.
        """
        matches = self.assert_json_path(path)._matches
        if not matches or not isinstance(matches[0], list):
            return []
        items = matches[0]
        return [item.get(field) for item in items if isinstance(item, dict)]

    def to_map(self, path: str, key_field: str) -> dict[str, Any]:
        """Convert an array of objects at path into a dictionary keyed by key_field.
        Supports 'Simple English' syntax.
        """
        matches = self.assert_json_path(path)._matches
        if not matches or not isinstance(matches[0], list):
            return {}
        items = matches[0]
        return {item[key_field]: item for item in items if isinstance(item, dict) and key_field in item}

    def to_list(self, path: str) -> list[Any]:
        """Convert a JSON object at path into a list of its values (Object -> Array).
        Supports 'Simple English' syntax.
        """
        matches = self.assert_json_path(path)._matches
        if not matches or not isinstance(matches[0], dict):
            return []
        obj = matches[0]
        return list(obj.values())

    def prettify(self, verbose: bool = True, max_length: int = 2000) -> ApiResponse:
        """Print the response JSON in a pretty-formatted style to the terminal and logs.
        
        Args:
            verbose: If False, only show minimal status (no body) on errors (default: True)
            max_length: Truncate output longer than this (default: 2000 chars)
        """
        # Check if response indicates error (4xx/5xx)
        is_error = self.status_code >= 400
        
        # Get output
        if self.json_data is not None:
            output = json.dumps(self.json_data, indent=4)
        else:
            output = self.text
        
        # Truncate if too long
        if len(output) > max_length:
            output = output[:max_length] + f"\n... [truncated {len(output) - max_length} chars]"
        
        # For errors, be quiet unless verbose=True
        if is_error and not verbose:
            # Just show status code, no body - user will see full error in assert_status
            print(f"[{self.status_code}] Error")
            return self
        
        # Full output for success or verbose mode
        import sys
        try:
            if sys.__stdout__ and sys.__stdout__.writable():
                sys.__stdout__.write(f"\n{output}\n")
                sys.__stdout__.flush()
            else:
                print(output)
        except Exception:
            print(output)
        
        # Also log
        import logging
        logging.getLogger("pyshaft.api").info(f"Response [{self.status_code}]:\n{output}")
        
        # 3. Attach to Allure Report if plugin is active
        try:
            import allure
            allure.attach(
                output, 
                name="API Response Body", 
                attachment_type=allure.attachment_type.JSON if self.json_data else allure.attachment_type.TEXT
            )
        except (ImportError, Exception):
            pass
            
        return self

    def assert_json_path(self, path: str, expected: Any = None) -> JsonSelector | ApiResponse:
        """Assert that a JSONPath query finds the expected value.
        
        Returns a JsonSelector if expected is None, allowing for .nth() selection.
        Supports 'Simple English' syntax: "meta variant" -> "$._meta.variant"
        """
        import jsonpath_ng
        normalized_path = self._normalize_path(path)
        expr = jsonpath_ng.parse(normalized_path)
        matches = [m.value for m in expr.find(self.json_data)]
        
        selector = JsonSelector(self, matches, normalized_path)
        if expected is not None:
            selector.should_be(expected)
            return self
        return selector

    def _normalize_path(self, path: str) -> str:
        """Converts 'English' paths to technical JSONPath (e.g., 'meta variant' -> '$._meta.variant')."""
        if path.startswith("$") or self.json_data is None:
            return path
            
        # 1. Normalize spaces to dots
        clean_path = path.replace(" ", ".")
        parts = [p for p in clean_path.split(".") if p]
        normalized = ["$"]
        
        current = self.json_data
        for part in parts:
            # Handle list markers like item[0] -> part='item', index='0'
            import re
            list_match = re.match(r"(\w+)\[(\d+)\]", part)
            if list_match:
                key, idx = list_match.groups()
                # Check direct or underscored key
                if isinstance(current, dict):
                    if key in current: target_key = key
                    elif f"_{key}" in current: target_key = f"_{key}"
                    else: target_key = key
                    
                    normalized.append(f"{target_key}[{idx}]")
                    try: current = current[target_key][int(idx)]
                    except (KeyError, IndexError, TypeError): current = None
                else:
                    normalized.append(part)
                    current = None
            else:
                # Standard key
                if isinstance(current, dict):
                    if part in current: target_key = part
                    elif f"_{part}" in current: target_key = f"_{part}"
                    else:
                        # Recursive Discovery: Try to find this key deeper in the tree
                        found_path = self._find_key_recursive(current, part)
                        if found_path:
                            target_key = found_path
                        else:
                            target_key = part
                    
                    normalized.append(target_key)
                    # Update current for the next segment in the path
                    try:
                        # If target_key is a nested path (from recursive discovery), we need to traverse it
                        temp = current
                        for subpart in target_key.split("."):
                            temp = temp[subpart]
                        current = temp
                    except (KeyError, TypeError):
                        current = None
                else:
                    normalized.append(part)
                    current = None
                    
        return ".".join(normalized)

    def _find_key_recursive(self, data: Any, target: str) -> str | None:
        """Find the first occurrence of a key (or _key) in a nested dictionary."""
        if not isinstance(data, dict):
            return None
            
        # 1. Search immediate children
        for key in data.keys():
            if key == target or key == f"_{target}":
                return key
                
        # 2. Search deeper
        for key, value in data.items():
            if isinstance(value, dict):
                res = self._find_key_recursive(value, target)
                if res:
                    return f"{key}.{res}"
            elif isinstance(value, list):
                for item in value:
                    res = self._find_key_recursive(item, target)
                    if res:
                        # Add wildcard targeting to iterate the array in JSONPath
                        return f"{key}[*].{res}"
        return None

    def _get_by_path(self, path: str) -> Any:
        """Internal helper to traverse JSON by dot/bracket notation."""
        if self.json_data is None:
            raise ValueError("Response does not contain valid JSON")
        
        import re
        # Convert brackets to dots: login[0].id -> login.0.id
        normalized = re.sub(r"\[(\d+)\]", r".\1", path)
        parts = normalized.split(".")
        
        current = self.json_data
        for part in parts:
            if part == "": continue
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
            else:
                return None
        return current

    def __repr__(self) -> str:
        return f"<ApiResponse [{self.status_code}]>"


class JsonSelector:
    """Chainable selector for JSON values, supporting multi-match selection via nth()."""

    def __init__(self, response: ApiResponse, matches: list[Any], path: str):
        self._response = response
        self._matches = matches
        self._path = path

    def nth(self, index: int) -> JsonSelector:
        """Select a specific match by index (1-indexed)."""
        idx = index - 1
        if idx < 0 or idx >= len(self._matches):
            raise IndexError(f"JSON match index {index} out of range (found {len(self._matches)} matches)")
        self._matches = [self._matches[idx]]
        return self

    def should_be(self, expected: Any) -> ApiResponse:
        """Assert that the selected JSON match(es) equal the expected value."""
        if not self._matches:
            raise AssertionError(f"No matches found for path: {self._path!r}")
            
        for match in self._matches:
            if match != expected:
                raise AssertionError(
                    f"JSON Mismatch at {self._path!r}\n"
                    f"Expected: {expected!r}\n"
                    f"Actual:   {match!r}"
                )
        return self._response

    def should_be_type(self, expected_type: str) -> ApiResponse:
        """Assert that the selected JSON match(es) are of a specific type.
        Supports common aliases: 'double', 'number', 'string', 'boolean', 'array', 'object'.
        """
        if not self._matches:
            raise AssertionError(f"No matches found for path: {self._path!r}")

        type_map = {
            "int": int, 
            "integer": int,
            "str": str, 
            "string": str,
            "float": float, 
            "double": float,
            "number": (int, float),
            "bool": bool,
            "boolean": bool,
            "list": list, 
            "array": list,
            "dict": dict, 
            "object": dict,
            "map": dict,
            "null": type(None),
            "none": type(None)
        }
        target = type_map.get(expected_type.lower())
        if target is None:
            raise ValueError(f"Unsupported type check: {expected_type}. Supported: {list(type_map.keys())}")

        for match in self._matches:
            if not isinstance(match, target):
                actual_type = type(match).__name__
                raise AssertionError(f"JSON Type Mismatch at {self._path!r}\nExpected: {expected_type}\nActual: {actual_type}")
        return self._response

    def should_contain(self, expected: Any) -> ApiResponse:
        """Assert that the selected JSON match(es) contain the expected value."""
        if not self._matches:
            raise AssertionError(f"No matches found for path: {self._path!r}")

        for match in self._matches:
            if isinstance(match, (list, str)):
                if expected not in match:
                    raise AssertionError(f"JSON match at {self._path!r} does not contain {expected!r}")
            elif isinstance(match, dict):
                if expected not in match:
                    raise AssertionError(f"JSON match at {self._path!r} does not contain key {expected!r}")
            else:
                raise TypeError(f"Cannot perform 'contains' on type {type(match).__name__}")
        return self._response

    def __repr__(self) -> str:
        return f"<JsonSelector path={self._path!r} matches={len(self._matches)}>"
