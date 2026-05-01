"""PyShaft API Inspector — Data importers for cURL and Postman."""

from __future__ import annotations

import argparse
import json
import logging
import re
import shlex
from dataclasses import dataclass, field
from typing import Any

from pyshaft.recorder.api_inspector.api_models import (
    ApiEnvironment,
    ApiFolder,
    ApiRequestStep,
    AuthType,
    HttpMethod,
)

logger = logging.getLogger("pyshaft.recorder.api_inspector.importers")


# ── Result container for Postman import ──────────────────────────────────

@dataclass
class PostmanImportResult:
    """Result of importing a Postman collection, includes items + variables."""
    items: list[ApiFolder | ApiRequestStep] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)
    collection_name: str = "Postman Import"


# ── cURL Parser ──────────────────────────────────────────────────────────

def parse_curl(curl_command: str) -> ApiRequestStep:
    """Parse a cURL command into an ApiRequestStep."""
    cmd = curl_command.strip()
    if not cmd.startswith("curl"):
        raise ValueError("Invalid cURL command: must start with 'curl'")

    try:
        cmd = cmd.replace("\\\n", " ").replace("\\\r\n", " ")
        tokens = shlex.split(cmd)[1:]  # skip 'curl'
    except ValueError as e:
        raise ValueError(f"Failed to parse cURL command: {e}")

    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default="")
    parser.add_argument("-X", "--request", dest="method", default="")
    parser.add_argument("-H", "--header", dest="headers", action="append", default=[])
    parser.add_argument("-d", "--data", dest="data", action="append", default=[])
    parser.add_argument("--data-raw", dest="data_raw", action="append", default=[])
    parser.add_argument("--data-binary", dest="data_binary", action="append", default=[])
    parser.add_argument("--data-urlencode", dest="data_urlencode", action="append", default=[])
    parser.add_argument("-u", "--user", dest="user", default="")
    parser.add_argument("-A", "--user-agent", dest="user_agent", default="")
    parser.add_argument("-e", "--referer", dest="referer", default="")

    known_args, _ = parser.parse_known_args(tokens)

    step = ApiRequestStep(name="cURL Import")
    url = known_args.url

    if not url:
        for t in reversed(tokens):
            if t.startswith("http://") or t.startswith("https://"):
                url = t
                break
    step.url = url

    method = "GET"
    has_data = bool(known_args.data or known_args.data_raw or known_args.data_binary or known_args.data_urlencode)

    if known_args.method:
        method = known_args.method.upper()
    elif has_data:
        method = "POST"

    try:
        step.method = HttpMethod(method)
    except ValueError:
        step.method = HttpMethod.GET

    headers = {}
    for h in known_args.headers:
        if ":" in h:
            k, v = h.split(":", 1)
            k = k.strip()
            v = v.strip()
            if k.lower() == "authorization":
                if v.lower().startswith("bearer "):
                    step.auth_type = AuthType.BEARER
                    step.auth_value = v[7:].strip()
                    continue
            headers[k] = v

    if known_args.user_agent:
        headers["User-Agent"] = known_args.user_agent
    if known_args.referer:
        headers["Referer"] = known_args.referer

    step.headers = headers

    if known_args.user:
        step.auth_type = AuthType.BASIC
        step.auth_value = known_args.user

    all_data = []
    all_data.extend(known_args.data)
    all_data.extend(known_args.data_raw)
    all_data.extend(known_args.data_binary)
    all_data.extend(known_args.data_urlencode)

    if all_data:
        payload = "&".join(all_data) if known_args.data_urlencode else "\n".join(all_data)
        try:
            parsed_json = json.loads(payload)
            step.payload = json.dumps(parsed_json, indent=2)
        except json.JSONDecodeError:
            step.payload = payload

    return step


# ── Postman Collection V2.1 Parser ───────────────────────────────────────

def parse_postman_collection(file_path: str) -> list[ApiFolder | ApiRequestStep]:
    """Parse a Postman Collection V2.1 into a list of items (Folders or Steps).

    Returns a single-element list containing a root folder named after the
    collection.  Variables are extracted but not returned here — use
    ``parse_postman_collection_full`` if you also need variables.
    """
    result = parse_postman_collection_full(file_path)
    return result.items


def parse_postman_collection_full(file_path: str) -> PostmanImportResult:
    """Full Postman import — returns items wrapped in a collection folder
    **and** extracted environment / collection variables."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "info" not in data or "schema" not in data["info"]:
        raise ValueError("Invalid Postman Collection format")

    result = PostmanImportResult()

    # ── 1. Collection name ───────────────────────────────────────────
    collection_name = data.get("info", {}).get("name", "Postman Import")
    result.collection_name = collection_name

    # ── 2. Extract collection-level variables ────────────────────────
    #   Postman stores them in "variable": [{"key": "k", "value": "v"}, ...]
    pm_vars = data.get("variable", [])
    for v in pm_vars:
        key = v.get("key", "")
        value = v.get("value", "")
        if key:
            result.variables[key] = value

    # ── 3. Also scan "auth" at collection level for variables ────────
    auth = data.get("auth", {})
    if auth:
        _extract_auth_variables(auth, result.variables)

    # ── 4. Parse items recursively ───────────────────────────────────
    parsed_items: list[ApiFolder | ApiRequestStep] = []
    if "item" in data:
        parsed_items = _traverse_items(data["item"])

    # ── 5. Scan all URLs for {{var}} patterns and register missing vars
    scan_and_register_template_vars(parsed_items, result.variables)

    # ── 6. Wrap in a root folder named after the collection ──────────
    root_folder = ApiFolder(name=collection_name, items=parsed_items)
    result.items = [root_folder]

    return result


def _extract_auth_variables(auth: dict, variables: dict[str, str]) -> None:
    """Pull auth tokens/keys into variables if they look like template vars."""
    auth_type = auth.get("type", "")
    entries = auth.get(auth_type, [])
    if isinstance(entries, list):
        for prop in entries:
            val = prop.get("value", "")
            if isinstance(val, str) and "{{" in val:
                var_name = val.strip("{} ")
                if var_name and var_name not in variables:
                    variables[var_name] = ""


def scan_and_register_template_vars(
    items: list[ApiFolder | ApiRequestStep],
    variables: dict[str, str],
) -> None:
    """Walk all steps and register any ``{{var}}`` templates that aren't
    already in the variables dict (sets them to empty string so they show
    up in the Variable Manager for the user to fill in)."""
    pattern = re.compile(r"\{\{([^}]+)\}\}")

    def _scan_step(step: ApiRequestStep) -> None:
        texts = [step.url, step.endpoint, step.payload, step.auth_value]
        texts.extend(step.headers.values())
        for text in texts:
            if not text:
                continue
            for match in pattern.finditer(text):
                var_name = match.group(1)
                if var_name not in variables:
                    variables[var_name] = ""

    def _scan_items(items_list: list) -> None:
        for item in items_list:
            if isinstance(item, ApiFolder):
                _scan_items(item.items)
            elif isinstance(item, ApiRequestStep):
                _scan_step(item)

    _scan_items(items)


def _traverse_items(pm_items: list[Any]) -> list[ApiFolder | ApiRequestStep]:
    """Recursively parse Postman items (folders + requests)."""
    items: list[ApiFolder | ApiRequestStep] = []
    for pm_item in pm_items:
        name = pm_item.get("name", "Unnamed")
        if "item" in pm_item:
            # Folder
            folder = ApiFolder(name=name)
            folder.items = _traverse_items(pm_item["item"])
            items.append(folder)
        elif "request" in pm_item:
            # Request
            req = pm_item["request"]
            step = _parse_postman_request(req, name)
            items.append(step)
    return items


def _parse_postman_request(req: dict[str, Any], name: str) -> ApiRequestStep:
    """Parse an individual Postman request dict."""
    step = ApiRequestStep(name=name)

    method_str = req.get("method", "GET").upper()
    try:
        step.method = HttpMethod(method_str)
    except ValueError:
        step.method = HttpMethod.GET

    url_data = req.get("url", "")
    if isinstance(url_data, dict):
        step.url = url_data.get("raw", "")
    elif isinstance(url_data, str):
        step.url = url_data

    headers = {}
    for h in req.get("header", []):
        if not h.get("disabled", False):
            headers[h.get("key", "")] = h.get("value", "")
    step.headers = headers

    auth = req.get("auth", {})
    if auth:
        auth_type = auth.get("type", "")
        if auth_type == "bearer":
            bearer_data = auth.get("bearer", [])
            for prop in bearer_data:
                if prop.get("key") == "token":
                    step.auth_type = AuthType.BEARER
                    step.auth_value = prop.get("value", "")
        elif auth_type == "basic":
            basic_data = auth.get("basic", [])
            user = ""
            pwd = ""
            for prop in basic_data:
                if prop.get("key") == "username":
                    user = prop.get("value", "")
                elif prop.get("key") == "password":
                    pwd = prop.get("value", "")
            step.auth_type = AuthType.BASIC
            step.auth_value = f"{user}:{pwd}"
        elif auth_type == "apikey":
            api_data = auth.get("apikey", [])
            key = ""
            val = ""
            for prop in api_data:
                if prop.get("key") == "key":
                    key = prop.get("value", "")
                elif prop.get("key") == "value":
                    val = prop.get("value", "")
            step.auth_type = AuthType.API_KEY
            step.auth_key = key
            step.auth_value = val

    body = req.get("body", {})
    if body:
        mode = body.get("mode")
        if mode == "raw":
            raw_content = body.get("raw", "")
            try:
                parsed_json = json.loads(raw_content)
                step.payload = json.dumps(parsed_json, indent=2)
            except json.JSONDecodeError:
                step.payload = raw_content
        elif mode == "urlencoded":
            params = []
            for p in body.get("urlencoded", []):
                if not p.get("disabled", False):
                    params.append(f"{p.get('key')}={p.get('value')}")
            step.payload = "&".join(params)

    return step


# ── Postman Environment File Parser ──────────────────────────────────────

def parse_postman_environment(file_path: str) -> dict[str, str]:
    """Parse a Postman Environment JSON file and return variables dict.

    Postman environments have the structure:
    { "name": "...", "values": [{"key": "k", "value": "v", "enabled": true}, ...] }
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    variables: dict[str, str] = {}
    for entry in data.get("values", []):
        if entry.get("enabled", True):
            variables[entry.get("key", "")] = entry.get("value", "")
    return variables


# ── PyShaft Script Parser ────────────────────────────────────────────────

def parse_pyshaft_script(file_path: str) -> list[ApiRequestStep]:
    """Basic parser to reverse engineer PyShaft API scripts.
    
    Looks for (api.request().method("url").body({...})...) patterns.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    steps: list[ApiRequestStep] = []
    
    # Very simple regex-based parser for V1
    # Matches: (api.request().post("url").body({...}).assert_status(200))
    blocks = re.findall(r"\(?\s*api\.request\(\).*?\)", content, re.DOTALL)
    
    for i, block in enumerate(blocks):
        step = ApiRequestStep(name=f"Imported Step {i+1}")
        
        # Method & URL
        m_match = re.search(r"\.(get|post|put|patch|delete|head)\(\"([^\"]+)\"\)", block)
        if m_match:
            step.method = HttpMethod(m_match.group(1).upper())
            step.url = m_match.group(2)
        
        # Body
        b_match = re.search(r"\.body\((.*?)\)\s*\.", block, re.DOTALL)
        if b_match:
            try:
                # Convert python-like dict to JSON
                body_str = b_match.group(1).strip()
                step.payload = body_str # In V1 we'll just keep it as is
            except: pass
            
        # Assertions
        status_match = re.search(r"\.assert_status\((\d+)\)", block)
        if status_match:
            step.expected_status = int(status_match.group(1))
            
        # JSONPath Equals
        a_matches = re.finditer(r"\.assert_json_path\(\"([^\"]+)\",\s*(.*?)\)", block)
        for am in a_matches:
            from pyshaft.recorder.api_inspector.api_models import ApiAssertion, AssertionType
            step.assertions.append(ApiAssertion(
                type=AssertionType.JSON_PATH_EQUALS,
                path=am.group(1),
                expected=am.group(2).strip("'\"")
            ))
            
        steps.append(step)
        
    return steps
