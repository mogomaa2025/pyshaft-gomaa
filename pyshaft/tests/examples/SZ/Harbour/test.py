import random

import pytest
from pyshaft import api, get, set, pipeline

baseURL = "https://api.restful-api.dev"
x_api_key = "80e7b0fb-5277-4767-8096-da0b1b39f5f3"


@pytest.mark.api
def test_get_collection():
    (api.request()
    .get(str(baseURL) + "/collections")
    .header("Content-Type", "application/json")
    .header("x-api-key", x_api_key)
    .log()
    .extract_json("[first].name", "nny")
    .assert_status(200))
    print("nny:", get("nny"))


@pytest.mark.api
def test_api():
    (api.request()
    .get(str(baseURL) + "/objects")
    .header("Content-Type", "application/json")
    .log()
    .extract_json("[last].name", "nny")
    .find_and_store("data", {"color": "Cloudy White"}, "found_item")
    .assert_status(200))
    print("nny:", get("nny"))

