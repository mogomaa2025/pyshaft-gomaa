"""PyShaft Complete Example - Shows all features for manual testers.

This file demonstrates:
1. Test data loading from CSV/JSON
2. Environment-specific configs
3. Extract & reuse pattern
4. Pytest markers and tags
5. Fixtures usage

Run with:
    pytest tests/examples/complete_example.py -v
    pytest tests/examples/complete_example.py -m smoke    # Run only smoke tests
    pytest tests/examples/complete_example.py -m api     # Run only API tests
"""

import pytest
from pyshaft import api
from pyshaft.testdata import load_test_data
from pyshaft.fixtures import test_env, store


# ==============================================================================
# Test Configuration
# ==============================================================================

# Mark this as an API test (no browser needed)
pytestmark = pytest.mark.api


# ==============================================================================
# Example 1: Basic Test with Environment
# ==============================================================================

@pytest.mark.smoke
def test_basic_get(test_env):
    """Simple GET request using environment config."""
    base_url = test_env["base_url"]
    print(f"Testing against: {base_url}")


# ==============================================================================
# Example 2: Using Test Data Files
# ==============================================================================

@pytest.mark.smoke
def test_with_csv_data():
    """Load test data from CSV file."""
    users = load_test_data("users")
    assert len(users) > 0
    print(f"Loaded {len(users)} users from CSV")

    # Use first user
    first_user = users[0]
    print(f"First user: {first_user['email']}")


# ==============================================================================
# Example 3: Extract and Reuse Pattern (IMPORTANT)
# ==============================================================================

@pytest.mark.smoke
def test_extract_and_reuse(store):
    """
    Step 1: Create resource and extract ID
    Step 2: Use extracted ID in next request
    """
    # This is the KEY pattern for chaining tests
    # The extract_json stores the value to .pyshaft_store.json
    # Use {{key}} to reference stored values

    # Example: Extract from response
    # api.post("/wharfs").extract_json("$.data.id", "wharf-id")
    # api.get("/wharfs/{{wharf-id}}")

    # For demo, let's store a value manually
    store.set("demo-value", 123)
    assert store.get("demo-value") == 123
    print(f"Stored value: {store.get('demo-value')}")


# ==============================================================================
# Example 4: Data-Driven Test
# ==============================================================================

@pytest.mark.regression
@pytest.mark.parametrize("user_id", [1, 2, 3])
def test_parametrized(user_id):
    """Run same test with different parameters."""
    print(f"Testing user ID: {user_id}")


# ==============================================================================
# Example 5: Chain Multiple Requests
# ==============================================================================

@pytest.mark.regression
def test_api_chain():
    """
    Chain multiple API calls.
    Each call can extract values for the next.
    """
    # This pattern allows you to:
    # 1. Login and get token
    # 2. Use token to get user profile
    # 3. Use profile ID to get user orders
    # 4. Use order ID to get order details

    # Example (pseudo-code):
    # (
    #     api.post("/login").body({"user": "admin"})
    #     .extract_json("$.token", "auth-token")
    #     .get("/profile").assert_status(200)
    #     .extract_json("$.id", "user-id")
    #     .get(f"/orders/{store.get('user-id')}")
    #     .assert_status(200)
    # )

    print("Chain test - placeholder")


# ==============================================================================
# Example 6: Using Fixtures
# ==============================================================================

def test_using_fixtures(test_data, load_data, store):
    """Demonstrate all available fixtures."""
    # test_data: dict of all loaded data files
    print(f"All data files: {list(test_data.keys())}")

    # load_data: function to load specific data
    users = load_data("users")
    print(f"Users: {len(users)}")

    # store: get/set/clear stored values
    store.set("test-key", "test-value")
    print(f"Stored: {store.get('test-key')}")
    print(f"All stored: {store.all()}")


# ==============================================================================
# Example 7: Error Handling with Retry
# ==============================================================================

from pyshaft.utils import retry


@pytest.mark.slow
@retry(max_attempts=3, backoff=1.5)
def test_with_retry():
    """Retry test up to 3 times on failure."""
    # Useful for flaky endpoints
    print("Running with retry...")
    # api.get("/unreliable-endpoint").assert_status(200)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])