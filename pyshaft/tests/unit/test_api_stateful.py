"""Unit tests for Stateful API and Implicit Execution."""

import pytest
from unittest.mock import MagicMock, patch
from pyshaft.api import api
from pyshaft.api.response import ApiResponse

class TestApiStateful:
    def setup_method(self):
        # Reset singleton state before each test
        api.clear()

    def test_stateful_standalone_lines(self):
        """Verify that separate lines build and execute correctly."""
        with patch("pyshaft.api.builder.RequestBuilder.perform") as mock_perform:
            # Mock a successful response
            mock_resp = MagicMock(spec=ApiResponse)
            mock_perform.return_value = mock_resp
            
            # --- The User's Desired Syntax ---
            api.request()
            api.post("http://ex.com/users")
            api.header("X-Test", "val")
            api.assert_status(201)  # This triggers perform() implicitly
            
            assert mock_perform.call_count == 1
            # Verify builder state was correct
            builder = api._current_builder
            assert builder._method == "POST"
            assert builder._url == "http://ex.com/users"
            assert builder._headers == {"X-Test": "val"}
            # Verify assertion was delegated
            mock_resp.assert_status.assert_called_with(201)

    def test_implicit_execution_one_liner(self):
        """Verify that .send() is not required for assertions."""
        with patch("pyshaft.api.builder.RequestBuilder.perform") as mock_perform:
            mock_resp = MagicMock(spec=ApiResponse)
            mock_perform.return_value = mock_resp
            
            # Chain without .send() or .perform()
            api.request().post("http://ex.com").assert_status(200)
            
            assert mock_perform.call_count == 1
            mock_resp.assert_status.assert_called_with(200)

    def test_direct_shortcut_standalone(self):
        """Verify that api.post() still works as a standalone one-liner."""
        with patch("pyshaft.api.send_post") as mock_send:
            mock_resp = MagicMock(spec=ApiResponse)
            mock_send.return_value = mock_resp
            
            # Standalone call (no api.request() before it)
            api.post("http://ex.com", {"id": 1}).assert_status(201)
            
            mock_send.assert_called_once()
            mock_resp.assert_status.assert_called_with(201)

    def test_perform_each_returns_list(self):
        """Verify perform_each still works and returns results list."""
        with patch("pyshaft.api.builder.RequestBuilder.perform") as mock_perform:
            mock_perform.return_value = MagicMock(spec=ApiResponse)
            
            results = api.request().post("/").with_data("id", [1, 2]).perform_each(lambda r: None)
            assert len(results) == 2
            assert mock_perform.call_count == 2
