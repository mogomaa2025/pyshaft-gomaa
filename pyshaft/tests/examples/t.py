import pytest
from pyshaft import web as w, tag, contain, text, role, textbox, placeholder, combobox, id_, heading


@pytest.mark.pyshaft_web
def test():
        (w.open_url("https://practicetestautomation.com/practice-test-login/")
        .type("student").exact(tag="input").nth(1)
        .type("Password123").exact(tag="input").nth(2)
        .click.contain(text="Submit").inside(id, "form")
        .assert_contain_title("Successfully")
        .assert_contain_text("Successfully").should_be_visible())

@pytest.mark.pyshaft_web
def test_dropdown1():
    (w.open_url("https://webdriveruniversity.com/Dropdown-Checkboxes-RadioButtons/index.html")
     .assert_aria_snapshot("- heading \"Dropdown Menu(s), Checkboxe(s) & Radio Button(s)\" [level=1]", role, heading)
     .select("Python", id_, "dropdowm-menu-1")
     .assert_text("Python", id_, "dropdowm-menu-1")
     .select("TestNG", id_, "dropdowm-menu-2")
     .assert_contain_text("NG", id_, "dropdowm-menu-2"))



