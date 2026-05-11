import pytest
from pyshaft import web as w

@pytest.mark.pyshaft_web
def test_search():
    w.open_url('https://example.com')
    w.assert_title('Example Domain')
