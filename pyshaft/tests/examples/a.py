import logging

import pytest

from pyshaft import api

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

@pytest.mark.pyshaft_api
def test_api_workflow():
    (
        api.request()
        .post("http://10.0.80.155:9090/EWebService-web/resources/wharfs/17")
        .prettify()
        .assert_status(200)

    )

swagger_base_url = "http://10.9.100.170"
@pytest.mark.pyshaft_api
def test_filter_importer_exporter():
    # Step 1: filter-importer-exporter
    (
        api.request()
        .get(str(swagger_base_url) + ":8090/EWebService-web/v1/importer-exporter?filtered=ewoiaWQiIDogNQp9")
        .prettify()
        .assert_status(200)
        .assert_json_path("$.message", "Success")
        .assert_json_path("$.success", True)
        .assert_json_type("$.timestamp", "str")
        .assert_json_path("$.data[0].eiAddress", "safasfasgasgas")

    )

youssef_base_url = "http://10.0.40.153"
def test_get_all_berths():
    # Step 1: get all berths
    (
        api.request()
        .get(str(youssef_base_url) + ":9090/EWebService-web/resources/berths")
        .prettify()
        .assert_status(200)
    )



def test_get_all_berths():
    # Step 1: get all berths
    (
        api.request()
        .get(str(youssef_base_url) + ":9090/EWebService-web/resources/berths")
        .prettify()
        .assert_status(200)
        .assert_json_contains("$[0].storeRegionName", "منطقة أولى")

    )

for i in range(3):
    @pytest.mark.pyshaft_api
    def test_test():
        api.request()
        api.get(str(youssef_base_url)+":9090/EWebService-web/resources/berths")
        api.assert_status(200)



body =({
  "id": "5",
  "name": "{{new-wharf-name}}",
  "portOfOperationId": 1,
  "unitId": 1,
  "length": 20,
  "extension": 6.0,
  "backExtension": 3.0,
  "allowFwdExtensionFlag": True,
  "allowBackExtensionFlag": False
} )
@pytest.mark.pyshaft_api
# @api.data_from_csv('data.csv')
# @api.data_from_json('data.json')
def test_get_agent_dashboard():
    # Step 1: GET Agent dashboard
    (
        api.request(body)
        .get(str(swagger_base_url) + ":8090/EWebService-web/v1/ship-visits/dashboard")
        .prettify()
        .assert_status(200)
    )




@pytest.mark.pyshaft_api
# @api.data_from_csv('data.csv')
# @api.data_from_json('data.json')
def test_get_all_berths():
    # Step 1: get all berths
    (
        api.request()
        .get(str(youssef_base_url) + ":9090/EWebService-web/resources/berths")
        .prettify()
        .assert_status(200)
    )
