"""PyShaft — Python test automation framework with semantic locators and auto-wait."""

__version__ = "0.1.0"

from pyshaft.config import get_config, load_config
from pyshaft.session import session_context
from pyshaft.api import api
from pyshaft.web import web
from pyshaft.web import (
    # Locator type constants
    role, text, label, placeholder, testid, id_, cls, css_, xpath, tag, attr, any_,
    # Text modifiers
    exact, contain, starts, contains,
    # HTML element types
    button, textbox, input_, checkbox, radio, link, menu, menuitem,
    dialog, modal, form, heading, alert, spinner, image, listbox, option, combobox,
    password, email, submit,
)
from pyshaft.utils import data_from_csv, data_from_json, data_from, retry, retry_on_exception, tag as test_tag
from pyshaft.testdata import TestDataManager, load_test_data, load_csv, load_json
from pyshaft.data_pipeline import pipeline, store_value, get_value
from pyshaft.data_decorators import data, data_from, parametrize

__all__ = [
    "__version__",
    "get_config",
    "load_config",
    "session_context",
    "api",
    "web",
    # Locator types
    "role", "text", "label", "placeholder", "testid", "id_", "cls", "css_", "xpath", "tag", "attr", "any_",
    "exact", "contain", "starts", "contains",
    "button", "textbox", "input_", "checkbox", "radio", "link", "menu", "menuitem",
    "dialog", "modal", "form", "heading", "alert", "spinner", "image", "listbox", "option", "combobox",
    "password", "email", "submit",
    # Utilities
    "data_from_csv",
    "data_from_json",
    "data_from",
    "retry",
    "retry_on_exception",
    "test_tag",
    # Test Data
    "TestDataManager",
    "load_test_data",
    "load_csv",
    "load_json",
    # Data Pipeline
    "pipeline",
    "store_value",
    "get_value",
    # Data Decorators (NEW!)
    "data",
    "parametrize",
]
