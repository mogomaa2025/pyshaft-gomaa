import pytest
from pyshaft import web as w, id_, password, placeholder, text


@pytest.mark.pyshaft_web
def test_untitled_test():
    (w.open_url("http://sczone.isfpdomain.com/login")
     .type("sps", placeholder, "SPS")
     .type("123456", id_, password)
     .click(text, "دخول").exact())

