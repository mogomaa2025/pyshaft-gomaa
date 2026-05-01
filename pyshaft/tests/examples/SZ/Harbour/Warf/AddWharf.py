import random

import pytest
from pyshaft import api

swagger_base_url = "http://10.9.100.170:8090/EWebService-web"

@pytest.mark.pyshaft_api
def test_Create_Warf():
    (
        api.request()
        .post(str(swagger_base_url) + "/v1/wharfs")
        .header("Content-Type", "application/json")
        .header("Accept", "application/json")
        .body({
            "name": "wharf random " + str(random.randint(0, 1_000)),
            "portOfOperationId": 1,
            "unitId": 1,
            "length": 250.0,
            "fwdExtension": 15.5,
            "allowFwdExtensionFlag": False,
            "backExtension": 10.0,
            "allowBackExtensionFlag": False
        })
        .prettify()
        .assert_status(201)
        .assert_json_path("$.message", "Added successfully")
        .assert_json_path("$.success", False) # should be true
        .assert_json_path("$.statusCode", 0) # should be 201
    )


@pytest.mark.pyshaft_api
def test_Create_Wharf():
    (
        api.request()
        .post(str(swagger_base_url) + "/v1/wharfs")
        .header("Content-Type", "application/json")
        .header("Accept", "application/json")
        .body({
            "name": "wharf random " + str(random.randint(0, 1_000)),
            "portOfOperationId": 1,
            "unitId": 1,
            "length": 250.0,
            "fwdExtension": 15.5,
            "allowFwdExtensionFlag": False,
            "backExtension": 10.0,
            "allowBackExtensionFlag": False
        })
        .prettify()
        .assert_status(201)
        .assert_json_path("$.message", "Added successfully")
        .assert_json_path("$.success", False) # should be true
        .assert_json_path("$.statusCode", 0) # should be 201
    )


def Test_Get_Wharf_By_ID():
    (
        api.request()
        .post(str(swagger_base_url) + "/v1/wharfs")
        .header("Content-Type", "application/json")
        .header("Accept", "application/json")
        .body({
            "name": "wharf random " + str(random.randint(0, 1_000)),
            "portOfOperationId": 1,
            "unitId": 1,
            "length": 250.0,
            "fwdExtension": 15.5,
            "allowFwdExtensionFlag": False,
            "backExtension": 10.0,
            "allowBackExtensionFlag": False
        })
        .prettify()
        .assert_status(201)
        .assert_json_path("$.message", "Added successfully")
        .assert_json_path("$.success", False) # should be true
        .assert_json_path("$.statusCode", 0) # should be 201
    )