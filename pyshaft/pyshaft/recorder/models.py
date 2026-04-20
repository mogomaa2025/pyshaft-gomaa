"""PyShaft Recorder — Data models for recorded steps and sessions."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class LocatorSuggestion:
    """A single locator strategy suggestion for an element."""
    locator_type: str       # role, id, text, css, xpath, testid, etc.
    value: str              # the locator value
    modifier: str | None = None  # exact, contain, starts
    stability: str = "high"      # high, medium, low
    score: int = 100             # 100 = best, 0 = worst

    def to_pyshaft(self) -> str:
        """Return PyShaft import-friendly constant name for the locator type."""
        type_map = {
            "role": "role", "text": "text", "label": "label",
            "placeholder": "placeholder", "testid": "testid",
            "id": "id_", "class": "cls", "css": "css_",
            "xpath": "xpath", "tag": "tag", "attr": "attr", "any": "any_",
        }
        return type_map.get(self.locator_type, self.locator_type)


@dataclass
class RecordedStep:
    """A single recorded test step (action or assertion)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action: str = "click"           # click, type, hover, scroll, assert_visible, open_url, etc.
    locator_type: str | None = None # role, id, text, css, xpath, etc.
    locator_value: str = ""         # the value to match
    modifier: str | None = None     # exact, contain, starts
    typed_text: str | None = None   # for type actions
    filters: dict = field(default_factory=dict)
    inside: tuple | None = None     # (type, value) for inside clause
    index: int | None = None        # nth index (1-based)
    assert_expected: str | None = None  # for assertions
    extract_variable: str | None = None  # variable name for get_text/get_value storage
    cast_type: str | None = None         # "int", "float", "str" for type casting
    assert_data_type_name: str | None = None  # expected type for assert_data_type
    timestamp: float = 0.0
    url: str = ""                   # page URL when step was recorded
    element_meta: dict = field(default_factory=dict)  # raw element metadata

    @property
    def category(self) -> str:
        """Return step category for color coding."""
        if self.action.startswith("assert") or self.action.startswith("should"):
            return "assert"
        if self.action in ("open_url", "go_back", "go_forward", "refresh"):
            return "nav"
        if self.action in ("wait", "sleep", "wait_until_disappears"):
            return "wait"
        if self.action in ("switch_to_iframe", "switch_to_default", "accept_alert", "dismiss_alert", "get_alert_text"):
            return "nav"
        if self.action.startswith("get_"):
            return "extract"
        return "action"

    @property
    def display_label(self) -> str:
        """Human-readable label for the step list."""
        parts = [self.action]
        if self.typed_text:
            parts.append(f'"{self.typed_text}"')
        if self.locator_type and self.locator_value:
            loc = f"{self.locator_type}={self.locator_value}"
            if self.modifier:
                loc = f"{self.locator_type}.{self.modifier}={self.locator_value}"
            parts.append(loc)
        elif self.locator_value:
            parts.append(self.locator_value)
        if self.index is not None:
            parts.append(f".nth({self.index})")
        if self.assert_expected:
            parts.append(f'expect="{self.assert_expected}"')
        if self.extract_variable:
            parts.append(f'→ {self.extract_variable}')
        if self.cast_type:
            parts.append(f'as {self.cast_type}')
        if self.assert_data_type_name:
            parts.append(f'type={self.assert_data_type_name}')
        return " ".join(parts)

    @property
    def icon(self) -> str:
        """Get icon for this step type."""
        from pyshaft.recorder.theme import ICONS
        icon_map = {
            "click": ICONS["click"], "double_click": ICONS["dblclick"],
            "right_click": ICONS["rightclick"], "type": ICONS["type"],
            "hover": ICONS["hover"], "scroll": ICONS["scroll"],
            "check": ICONS["check"], "uncheck": ICONS["uncheck"],
            "select": ICONS["select"], "submit": ICONS["submit"],
            "drag": ICONS["drag"], "open_url": ICONS["nav"],
            "go_back": ICONS["nav"], "go_forward": ICONS["nav"],
            "refresh": ICONS["nav"],
            "assert_visible": ICONS["visible"], "assert_hidden": ICONS["hidden"],
            "assert_text": ICONS["text"], "assert_enabled": ICONS["enabled"],
            "assert_disabled": ICONS["disabled"], "assert_checked": ICONS["check"],
            "assert_title": ICONS["title"], "assert_url": ICONS["url"],
            "assert_contain_text": ICONS["text"],
            "assert_contain_title": ICONS["title"],
            "assert_contain_url": ICONS["url"],
            "assert_snapshot": ICONS["visible"],
            "assert_selected_option": ICONS["dropdown"],
            "assert_contain_selected": ICONS["dropdown"],
            "assert_data_type": ICONS["data_type"],
            "assert_value": ICONS["get_value"],
            "get_text": ICONS["get_text"],
            "get_value": ICONS["get_value"],
            "get_text_as_int": ICONS["cast_int"],
            "get_text_as_float": ICONS["cast_float"],
            "get_text_as_str": ICONS["get_text"],
            "get_selected_option": ICONS["dropdown"],
            "select_dynamic": ICONS["select"], "upload_file": ICONS["nav"],
            "remove_element": "🗑", "wait_until_disappears": "⏳",
            "switch_to_iframe": "🪟", "switch_to_default": "↩",
            "accept_alert": "✓", "dismiss_alert": "✕", "get_alert_text": "💬",
            "pick_date": "📅",
        }
        return icon_map.get(self.action, "•")

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON export."""
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "RecordedStep":
        """Deserialize from dictionary."""
        # Handle tuple fields
        inside = data.get("inside")
        if isinstance(inside, list):
            data["inside"] = tuple(inside)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RecordingSession:
    """A recording session containing multiple steps."""
    name: str = "Untitled Test"
    steps: list[RecordedStep] = field(default_factory=list)
    start_url: str = ""
    created_at: float = 0.0
    modified_at: float = 0.0
    metadata: dict = field(default_factory=dict)

    def add_step(self, step: RecordedStep) -> None:
        """Add a step to the session."""
        self.steps.append(step)

    def remove_step(self, step_id: str) -> None:
        """Remove a step by ID."""
        self.steps = [s for s in self.steps if s.id != step_id]

    def move_step(self, from_index: int, to_index: int) -> None:
        """Move a step from one position to another."""
        if 0 <= from_index < len(self.steps) and 0 <= to_index < len(self.steps):
            step = self.steps.pop(from_index)
            self.steps.insert(to_index, step)

    def get_step(self, step_id: str) -> RecordedStep | None:
        """Get a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def duplicate_step(self, step_id: str) -> RecordedStep | None:
        """Duplicate a step and insert it after the original."""
        for i, step in enumerate(self.steps):
            if step.id == step_id:
                new_step = RecordedStep(**{
                    k: v for k, v in asdict(step).items()
                    if k != "id"
                })
                if isinstance(step.inside, tuple):
                    new_step.inside = step.inside
                self.steps.insert(i + 1, new_step)
                return new_step
        return None

    def to_json(self) -> str:
        """Serialize the session to JSON."""
        data = {
            "name": self.name,
            "start_url": self.start_url,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "metadata": self.metadata,
            "steps": [step.to_dict() for step in self.steps],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "RecordingSession":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        session = cls(
            name=data.get("name", "Untitled Test"),
            start_url=data.get("start_url", ""),
            created_at=data.get("created_at", 0.0),
            modified_at=data.get("modified_at", 0.0),
            metadata=data.get("metadata", {}),
        )
        for step_data in data.get("steps", []):
            session.steps.append(RecordedStep.from_dict(step_data))
        return session
