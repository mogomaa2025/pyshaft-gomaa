import random

import pytest
from pyshaft import api, get, set, pipeline

baseURL = "http://10.9.100.170:8090/EWebService-web/v1"
wharf_length = 10000
berth_new_beta = "B55" + str(random.randint(500, 9_000))
berth_new_starting_point = random.randint(1, 2_000)


@pytest.mark.pyshaft_api
def test_Create_Unique_Wharf():
    """Create a new wharf and store the ID for next tests."""
    (
        api.request()
        .post(str(baseURL) + "/wharfs")
        .header("Content-Type", "application/json")
        .log()  # Shows: method, URL, request body, response body
        .body({
            "name": "wharf random " + str(random.randint(0, 1_000)),
            "portOfOperationId": 1,
            "unitId": 1,
            "length": wharf_length,
            "extension": 6.0,
            "backExtension": 3.0,
            "allowFwdExtensionFlag": True,
            "allowBackExtensionFlag": False
        })
        .assert_status(201)
        .extract_json("$.data.id", "wharf_id")
    )


@pytest.mark.pyshaft_api
def test_Get_Wharf_By_ID():
    """Get wharf using stored ID."""
    wharf_id = get("wharf_id")
    print(f"Using wharf_id: {wharf_id}")
    
    (
        api.request()
        .get(str(baseURL) + f"/wharfs/{wharf_id}")
        .assert_status(200)
    )


@pytest.mark.pyshaft_api
def test_create_berth():
    """Create a berth for the wharf."""
    wharf_id = get("wharf_id")
    
    (
        api.post(str(baseURL) + "/v1/berths")
        .header("Content-Type", "application/json")
        .body({
            "name": "new berth " + str(random.randint(0, 1_000)),
            "startPointFT": 350,
            "lengthFT": 200,
            "depthFT": 60,
            "isRoro": "0",
            "isSingleVessel": "1",
            "hasPhone": "1",
            "isSamplesPreview": "0",
            "allowFloatingDock": "0",
            "isSeasideDischarge": "1",
            "guardExemption": "0",
            "historicStatement": "0",
            "isMerged": "0",
            "isSplited": "0",
            "orderNumber": 10,
            "maxLoad": 500000,
            "storeRegionId": 1,
            "wharfId": wharf_id,
            "shipTypeIds": [6, 8, 14],
            "productIds": [1, 2],
            "visitReasonIds": [1, 2],
            "betas": [
                {"name": berth_new_beta, "startPointOnWharf": berth_new_starting_point}
            ]
        })
        .log()
        .assert_status(201)
    )


@pytest.mark.pyshaft_api
def test_Get_Wharf_By_Placeholder():
    """Use placeholder syntax with stored wharf_id."""
    (
        api.request()
        .get(str(baseURL) + "/v1/wharfs/{{wharf_id}}")
        .header("Accept", "application/json")
        .log()
        .assert_status(200)
        .assert_json_contains("$.name", "wharf random ")
    )


@pytest.mark.pyshaft_api
def test_Fluent_Pipeline_Example():
    """Example of using pipeline for fluent chaining."""
    # Store multiple values
    pipeline.set("user_id", 123).set("token", "abc123")
    
    # Get stored values
    user_id = pipeline.get("user_id")
    token = pipeline.get("token")
    
    # Use in request
    (
        api.get(f"/users/{user_id}")
        .header("Authorization", f"Bearer {token}")
        .log()
        .assert_status(200)
    )


@pytest.mark.pyshaft_api
def test_Direct_Set_Get():
    """Direct set and get without chaining."""
    # Direct set
    set("my_key", "my_value")
    
    # Direct get
    value = get("my_key")
    print(f"Retrieved: {value}")