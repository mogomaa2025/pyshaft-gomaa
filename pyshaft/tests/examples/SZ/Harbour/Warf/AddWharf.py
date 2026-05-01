import random

import pytest
from pyshaft import api, pipeline, get_value

swagger_base_url = "http://10.9.100.170:8090/EWebService-web"
youssef_delpoy_url = "http://10.0.40.153:9090/EWebService-web"

wharf_length = 20000
berth_new_beta = "B55" + str(random.randint(500, 9_000))
berth_new_starting_point = random.randint(1, 2_000)


@pytest.mark.pyshaft_api
def test_Create_Wharf():
    """Create wharf and store ID in both store file AND pipeline (memory)."""
    (
        api.request()
        .post(str(swagger_base_url) + "/v1/wharfs")
        .header("Content-Type", "application/json")
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
    pipeline.set("wharf_id", api.stored("wharf_id")) # SET


@pytest.mark.pyshaft_api
def test_Get_Wharf_By_ID():
    """Use wharf_id from pipeline (memory) instead of file."""
    wharf_id = get_value("wharf_id") # GET
    print(f"Using wharf_id from pipeline: {wharf_id}")
    
    (
        api.request()
        .get(str(swagger_base_url) + f"/v1/wharfs/{wharf_id}")
        .assert_status(200)
    )


@pytest.mark.pyshaft_api
def test_create_berth():
    """Use pipeline to get wharf_id."""
    wharf_id = get_value("wharf_id")  # GET
    (
        api.post(str(swagger_base_url) + "/v1/berths")
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
        .assert_status(201)
    )

'''make sure wharf created'''
@pytest.mark.pyshaft_api
def test_Get_Wharf_By_ID():
    (
        api.request()
        .get(str(swagger_base_url) + "/v1/wharfs/{{wharf_id}}")
        .header("Accept", "application/json")
        .prettify(verbose=False)
        .assert_status(200)
        .assert_json_contains("$.name", "wharf random ")
    )



"""Uses same wharf_id : create berth"""
@pytest.mark.pyshaft_api
def test_create_berth():
    wharf_id = get_value("wharf_id")  # GET
    (
        api.post(str(youssef_delpoy_url) + "/v1/berths")
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
        .prettify(verbose=False)
        .assert_status(201)
    )
