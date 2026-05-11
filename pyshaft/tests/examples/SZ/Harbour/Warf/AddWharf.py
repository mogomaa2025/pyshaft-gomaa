import random

import pytest
from pyshaft import api

swagger_base_url = "http://10.9.100.170:8090/EWebService-web"
youssef_delpoy_url = "http://10.0.40.153:9090/EWebService-web"

wharf_length = 20000
berth_new_beta = "B55" + str(random.randint(500, 9_000))
berth_new_starting_point = random.randint(1, 2_000_000)


'''create partent wharf to use in berth'''
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
            "length": wharf_length,
            "extension": 6.0,
            "backExtension": 3.0,
            "allowFwdExtensionFlag": True,
            "allowBackExtensionFlag": False
        })
        .prettify()
        .assert_status(201)
        .assert_json_path("$.message", "Added successfully")
        .extract_json("$.data", "wharf-id")
    )

'''make sure wharf created'''
@pytest.mark.pyshaft_api
def test_Get_Wharf_By_ID():
    (
        api.request()
        .get(str(swagger_base_url) + "/v1/wharfs/{{wharf-id}}")
        .header("Accept", "application/json")
        .prettify()
        .assert_status(200)
        .assert_json_contains("$.name", "wharf random ")
    )

@pytest.mark.pyshaft_api
def test_create_berth():
    wharf_id = str("{{wharf-id}}")
    (
        api.request()
        .post(str(youssef_delpoy_url) + "/v1/berths")
        .header("Content-Type", "application/json")
        .body({
            "name": "new wharf random dsfdsf" + str(random.randint(0, 1_000)),
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
            "wharfId": "{{wharf-id}}",
            "shipTypeIds": [6, 8, 14],
            "productIds": [1, 2],
            "visitReasonIds": [1, 2],
            "betas": [
                {"name": berth_new_beta, "startPointOnWharf": berth_new_starting_point}
            ]
        })
        .prettify()
        .assert_status(201)
    )
