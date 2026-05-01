"""Example API test - Basic usage for manual testers.

This file shows how to write API tests in PyShaft.
Copy this pattern to create your own tests.

Usage:
    pytest tests/examples/api_basic_example.py -v
"""

import pytest
from pyshaft import api


BASE_URL = "http://10.9.100.170:8090/EWebService-web"


class TestBasicAPI:
    """Basic API test examples."""

    def test_get_request(self):
        """Simple GET request example."""
        response = (
            api.get(f"{BASE_URL}/v1/users")
            .assert_status(200)
        )
        print(f"Response: {response.json()}")

    def test_post_with_body(self):
        """POST request with JSON body."""
        (
            api.post(f"{BASE_URL}/v1/wharfs")
            .header("Content-Type", "application/json")
            .body({
                "name": "Test Wharf",
                "portOfOperationId": 1,
                "unitId": 1,
                "length": 200
            })
            .assert_status(201)
            .assert_json_path("$.message", "Added successfully")
        )

    def test_extract_and_reuse(self):
        """Extract value from response and reuse in next request."""
        # Step 1: Create resource and extract ID
        (
            api.post(f"{BASE_URL}/v1/wharfs")
            .header("Content-Type", "application/json")
            .body({
                "name": "Extract Test Wharf",
                "portOfOperationId": 1,
                "unitId": 1,
                "length": 100
            })
            .assert_status(201)
            .extract_json("$.data.id", "wharf-id")  # Store ID as "wharf-id"
        )

        # Step 2: Use stored ID in next request
        (
            api.get(f"{BASE_URL}/v1/wharfs/{{wharf-id}}")
            .assert_status(200)
            .assert_json_contains("$.name", "Extract Test Wharf")
        )

    def test_with_test_data(self):
        """Use data from test data file."""
        from pyshaft.testdata import load_test_data

        users = load_test_data("users")
        for user in users:
            print(f"Testing with user: {user['email']}")
            # Use user data in your test
            assert "@" in user["email"]


class TestDataDrivenAPI:
    """Data-driven API tests using pytest markers."""

    @pytest.mark.parametrize("user", [
        {"email": "user1@test.com", "name": "User One"},
        {"email": "user2@test.com", "name": "User Two"},
    ])
    def test_multiple_users(self, user):
        """Test with multiple user data."""
        (
            api.post(f"{BASE_URL}/v1/users")
            .body({"email": user["email"], "name": user["name"]})
            .assert_status(201)
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])