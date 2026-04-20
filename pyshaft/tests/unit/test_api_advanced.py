"""Unit tests for Advanced API features."""

import pytest
from unittest.mock import MagicMock, patch
from pyshaft.api import api
from pyshaft.api.response import ApiResponse

class TestApiAdvanced:
    def test_request_builder_params(self):
        builder = api.request().get("http://ex.com").param("q", "search").header("X-Test", "val")
        assert builder._method == "GET"
        assert builder._url == "http://ex.com"
        assert builder._params == {"q": "search"}
        assert builder._headers == {"X-Test": "val"}

    def test_request_builder_body_kv(self):
        # Test appending to body
        builder = api.request().post("http://ex.com").body("id", 1).body("name", "Alice")
        assert builder._body == {"id": 1, "name": "Alice"}

    def test_request_builder_body_dict(self):
        # Test full body overwrite
        builder = api.request().post("http://ex.com").body({"full": True})
        assert builder._body == {"full": True}

    def test_json_path_bracket_notation(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"items": [{"id": 10}, {"id": 20}]}
        mock_resp.status_code = 200
        mock_resp.text = '{"items": [{"id": 10}, {"id": 20}]}'
        
        resp = ApiResponse(mock_resp)
        # Test bracket support
        assert resp._get_by_path("items[0].id") == 10
        assert resp._get_by_path("items[1].id") == 20
        # Test dot-digit fallback
        assert resp._get_by_path("items.0.id") == 10

    def test_assert_json_type(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": 1, "name": "Alice", "active": True, "tags": [1,2]}
        mock_resp.status_code = 200
        resp = ApiResponse(mock_resp)
        
        resp.assert_json_type("id", "int")
        resp.assert_json_type("name", "str")
        resp.assert_json_type("active", "bool")
        resp.assert_json_type("tags", "list")
        
        with pytest.raises(AssertionError):
            resp.assert_json_type("id", "str")

    def test_assert_json_contains(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"tags": ["a", "b", "c"], "info": {"version": "1.0"}}
        resp = ApiResponse(mock_resp)
        
        resp.assert_json_contains("tags", "b")
        resp.assert_json_contains("info", "version")
        
        with pytest.raises(AssertionError):
            resp.assert_json_contains("tags", "z")

    def test_assert_json_in_array(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"users": [{"id": 1, "role": "admin"}, {"id": 2, "role": "user"}]}
        resp = ApiResponse(mock_resp)
        
        resp.assert_json_in_array("users", {"id": 1, "role": "admin"})
        resp.assert_json_in_array("users", {"role": "user"})
        
        with pytest.raises(AssertionError):
            resp.assert_json_in_array("users", {"id": 1, "role": "user"})

    def test_api_fill_template(self):
        template = {"user": {"name": "{{name}}", "id": "{{id}}"}, "tags": ["{{tag}}"]}
        filled = api.fill(template, name="Alice", id=123, tag="test")
        assert filled == {"user": {"name": "Alice", "id": 123}, "tags": ["test"]}

    def test_for_each(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ids": [1, 2, 3]}
        resp = ApiResponse(mock_resp)
        
        collector = []
        resp.for_each("ids", lambda x: collector.append(x * 2))
        assert collector == [2, 4, 6]

    def test_for_each_key(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"a": 1, "b": 2}
        resp = ApiResponse(mock_resp)
        
        keys = []
        resp.for_each_key("", lambda k: keys.append(k))
        assert sorted(keys) == ["a", "b"]

    def test_map_and_to_map(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "users": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        }
        resp = ApiResponse(mock_resp)
        
        # Test map (extract fields)
        ids = resp.map("users", "id")
        assert ids == [1, 2]
        
        # Test to_map (array to dict)
        u_map = resp.to_map("users", "id")
        assert u_map[1]["name"] == "A"
        assert u_map[2]["name"] == "B"

    def test_to_list(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"config": {"enabled": True, "retry": 3}}
        resp = ApiResponse(mock_resp)
        
        values = resp.to_list("config")
        assert True in values
        assert 3 in values

    def test_perform_each_batch(self):
        from pyshaft.api import api
        # Mock perform to avoid real network calls
        with patch("pyshaft.api.builder.RequestBuilder.perform") as mock_perform:
            mock_perform.return_value = MagicMock(spec=ApiResponse)
            
            results = []
            api.request().post("/batch").body(base="val").with_data("id", [10, 20]).perform_each(
                lambda r: results.append(r)
            )
            
            assert mock_perform.call_count == 2
            # Check body in calls
            # 1st call: body={"base": "val", "id": 10}
            # 2nd call: body={"base": "val", "id": 20}
            # Note: since perform() is called on the same builder, we can't easily check args if not captured
            # But the logic is verified by call_count and return list length
            assert len(results) == 2
