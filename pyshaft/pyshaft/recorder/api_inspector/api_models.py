"""PyShaft API Inspector — Data models for API request/response recording."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class HttpMethod(StrEnum):
    """Supported HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthType(StrEnum):
    """Authentication types."""
    NONE = "none"
    BEARER = "bearer"
    BASIC = "basic"
    API_KEY = "api_key"
    ENV_VAR = "env_var"


class AssertionType(StrEnum):
    """API response assertion types."""
    STATUS_CODE = "status_code"
    JSON_PATH_EQUALS = "json_path_equals"
    JSON_PATH_CONTAINS = "json_path_contains"
    JSON_PATH_TYPE = "json_path_type"
    JSON_PATH_DATE = "json_path_date"
    JSON_PATH_UUID = "json_path_uuid"
    RESPONSE_CONTAINS = "response_contains"
    HEADER_EQUALS = "header_equals"
    RESPONSE_TIME_LT = "response_time_lt"
    JSON_SCHEMA = "json_schema"
    DEEP_EQUALS = "deep_equals"
    DEEP_CONTAINS = "deep_contains"


class PipelineOp(StrEnum):
    """Pipeline operations for response data transformation."""
    MAP = "map"
    FLATTEN = "flatten"
    REDUCE = "reduce"
    FILTER = "filter"
    SORT = "sort"
    FIRST = "first"
    LAST = "last"
    COUNT = "count"
    UNIQUE = "unique"


@dataclass
class ApiAssertion:
    """Single assertion on an API response."""
    type: AssertionType
    path: str = ""          # JSONPath or header name
    expected: str = ""      # Expected value
    expected_type: str = "" # For type checking (int, str, etc.)


@dataclass
class ApiExtraction:
    """Variable extraction from API response."""
    variable_name: str
    json_path: str
    cast_type: str = "str"  # "str", "int", "float", "bool"


@dataclass
class PipelineStep:
    """Single pipeline transformation step."""
    operation: PipelineOp
    path: str = ""         # JSONPath to operate on
    expression: str = ""   # Lambda expression for map/filter/reduce
    key: str = ""          # Sort key or reduce accumulator


@dataclass(eq=False)
class ApiRequestStep:
    """A single API request in the workflow."""
    name: str = "Request"
    method: HttpMethod = HttpMethod.GET
    url: str = ""
    endpoint: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    payload: str = ""     # JSON string
    auth_type: AuthType = AuthType.NONE
    auth_value: str = ""  # Token, env var name, etc.
    auth_key: str = ""    # Header name for API key

    # Expected response
    expected_status: int = 200

    # Assertions
    assertions: list[ApiAssertion] = field(default_factory=list)

    # Extractions (save response values to variables)
    extractions: list[ApiExtraction] = field(default_factory=list)

    # Pipeline (transform response data)
    pipeline: list[PipelineStep] = field(default_factory=list)

    # Loop support
    loop_variable: str = ""      # Variable name containing the array
    loop_payload_key: str = ""   # Key in payload to substitute with loop item

    # Query Parameters (from Params tab)
    query_params: dict[str, str] = field(default_factory=dict)
    
    # Base64-Encoded Query Parameter
    b64_param_name: str = ""
    b64_param_json: str = ""
    b64_param_encoded: str = ""

    # Execution result (populated after running)
    last_status: int | None = None
    last_response: Any = None
    last_duration_ms: float = 0.0
    last_error: str | None = None

    # Retry logic (chainable)
    retry_count: int = 0  # 0 = no retry
    retry_mode: str = "all"  # all, timeout, fail, or exception/status
    retry_backoff: float = 1.0  # multiplier for backoff (1.0 = no backoff)


@dataclass
class ApiEnvironment:
    """A set of variables for a specific environment (Dev, Prod, etc.)."""
    name: str
    variables: dict[str, str] = field(default_factory=dict)
    base_url: str = ""


@dataclass(eq=False)
class ApiFolder:
    """A folder to organize API requests."""
    name: str = "New Folder"
    items: list[ApiFolder | ApiRequestStep] = field(default_factory=list)


@dataclass
class ApiWorkflow:
    """Complete API test workflow (collection of requests)."""
    name: str = "API Workflow"
    base_url: str = ""
    # items can contain both folders and direct steps (root items)
    items: list[ApiFolder | ApiRequestStep] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)  # Default/Global variables
    
    # Environment support
    environments: list[ApiEnvironment] = field(default_factory=list)
    current_environment_index: int = -1
    
    # Global state
    global_headers: dict[str, str] = field(default_factory=dict)
    use_session: bool = True  # Whether to share cookies across steps

    @property
    def all_steps(self) -> list[ApiRequestStep]:
        """Flattened list of all steps in the tree."""
        steps = []
        def _collect(items):
            for it in items:
                if isinstance(it, ApiRequestStep):
                    steps.append(it)
                elif isinstance(it, ApiFolder):
                    _collect(it.items)
        _collect(self.items)
        return steps
