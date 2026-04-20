import logging

import pytest

from pyshaft import api

# Configure logging to see prettify() output even without -s (in some environments)
logging.basicConfig(level=logging.INFO)

name = "Add your name in the body"
body =({
	"name": name
})

def test_api_post():
    (api.request()
      .post("https://postman-echo.com/post")
      .body(body)
      # .header("x-api-key", "reqres_e3d2529960164c6db3189223e630b8e1")
      .prettify()
      .assert_status(200)
      .assert_json_path("name",name))


@pytest.mark.pyshaft_api
@pytest.mark.parametrize("")
def test_api_workflow():
    var = "gomaa"
    # Step 1: Request 1
    (
        api.request()
        .post("https://postman-echo.com/post")
        .body({
                "name": var
            })
        .prettify()
        .assert_status(200)
        .assert_json_type("$.headers.content-length", "str")
        .assert_json_path("$.data.name", var)
        .extract_json("$.headers.content-length", "ll")
    )

