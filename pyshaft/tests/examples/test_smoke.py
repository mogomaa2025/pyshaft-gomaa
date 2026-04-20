"""PyShaft smoke test — verifies the basic framework pipeline works."""

from pyshaft.web import web


def test_google_title():
    """Open Google and verify the page title."""
    open_url("https://www.google.com")
    assert_title("Google")


def test_example_domain():
    """Open example.com and verify the page title."""
    open_url("https://example.com")
    assert_title("Example Domain")
