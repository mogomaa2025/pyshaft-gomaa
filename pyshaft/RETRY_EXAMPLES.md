"""
PyShaft Retry Feature Examples

This file demonstrates how to use the chainable retry feature in both web and API modules.
"""

# ============================================================================
# WEB MODULE RETRY EXAMPLES
# ============================================================================

# Example 1: Retry on any exception (default)
# w.click(role, button).retry(3).execute()

# Example 2: Retry only on timeout
# w.click(role, button).retry(2, "timeout").execute()

# Example 3: Retry only on assertion/find failures
# w.assert_text("hello", role, div).retry(3, "fail")

# Example 4: Retry with custom exception type
# from selenium.common.exceptions import NoSuchElementException
# w.click(role, button).retry(2, NoSuchElementException)

# Example 5: Retry with custom backoff
# w.click(role, button).retry(3, "all", backoff=2.0).execute()

# Example 6: Chain multiple operations with retry
# w.click(role, button).retry(2, "timeout") \
#  .type("hello", role, input).retry(3, "fail") \
#  .assert_text("Success", role, message)


# ============================================================================
# API MODULE RETRY EXAMPLES
# ============================================================================

# Example 1: Basic retry on any error
# api.post("/users").body("name", "Bob").retry(3).send().assert_status(201)

# Example 2: Retry only on timeout
# api.get("/users/1").retry(2, "timeout").send().assert_status(200)

# Example 3: Retry only on assertion failures
# api.post("/data").retry(3, "fail").send().assert_status(201).assert_json("id", 123)

# Example 4: Retry on specific HTTP status code
# api.get("/data").retry(3, 500).send().assert_status(200)  # Retries if 500 status

# Example 5: Retry with custom backoff
# api.post("/users").retry(4, "all", backoff=1.5).send().assert_status(201)

# Example 6: Retry at builder level
# api.request() \
#     .post("/users") \
#     .body("name", "Bob") \
#     .retry(3, "fail") \
#     .send() \
#     .assert_status(201) \
#     .assert_json("success", True)


# ============================================================================
# REAL-WORLD TEST EXAMPLES
# ============================================================================

def test_login_with_retry():
    """Example: Login test with retry on timeout"""
    from pyshaft.web import web as w
    
    w.open_url("https://example.com/login")
    # If button click times out, retry up to 3 times with exponential backoff
    w.click("role", "button").retry(3, "timeout").execute()
    w.type("admin", "role", "textbox").filter(placeholder="Username")
    w.type("password", "role", "textbox").filter(placeholder="Password")
    w.click("role", "button").contain(text="Submit")
    # Assert success message appears (retry if assertion fails)
    w.assert_text("Login successful", "role", "status").retry(3, "fail")


def test_api_with_status_retry():
    """Example: API test with retry on specific status code"""
    from pyshaft.api import api
    
    # Retry if we get a 500 error, up to 3 times
    api.get("/data").retry(3, 500).send() \
        .assert_status(200) \
        .assert_json("status", "ok") \
        .extract_json("data[0].id", "item_id")


def test_flaky_assertion():
    """Example: Retry on assertion failures due to timing issues"""
    from pyshaft.web import web as w
    
    w.open_url("https://example.com")
    w.click("role", "button")  # Click to trigger async operation
    # Wait for message to appear, retry assertion if it fails (element not found)
    w.assert_text("Processing complete", "role", "message").retry(5, "fail")

