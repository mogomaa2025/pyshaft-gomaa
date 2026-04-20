import pytest
from pyshaft import web as w , role, textbox, button, placeholder, modal, text, contain, contains

@pytest.mark.pyshaft_web
def test():
    w.open_url("https://smarterp.isfpegypt.com/HR-web2/")
    
    # Verify 3-argument modifier pattern
    w.type("mohgomaa", "id", "j_username")
    w.type("wrong_pass", "id", "j_password")
    
    # Verify 'contains' modifier fix & 3-arg pattern
    w.click(text, contains, "الدخول")
    
    # Verify new containment assertions with actual page values
    # w.assert_contain_title("تسجيل")  # Arabic for "Registration/Login"
    #w.assert_contain_url("HR-web2")
    w.assert_contain_title()
    
    # Verify error message visibility
    w.assert_visible("css=.alert-danger", timeout=5)