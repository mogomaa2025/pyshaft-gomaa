import pytest
from pyshaft import web as w, tag, contain, text, role, textbox


@pytest.mark.pyshaft_web
def test():
        (w.open_url("https://practicetestautomation.com/practice-test-login/")
        .type("student").exact(tag="input").nth(1)
        .type("Password123").exact(tag="input").nth(2)
        .click.contain(text="Submit").inside(id, "form")
        .assert_contain_title("Successfully")
        .assert_contain_text("Successfully").should_be_visible())
