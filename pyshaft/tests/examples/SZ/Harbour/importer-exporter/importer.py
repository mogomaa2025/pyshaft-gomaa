import random

import pytest
from pyshaft import api, get_value, extract

swagger_base_url = "http://10.9.100.170:8090/EWebService-web"


@extract("$.data", "exporter_id")
@pytest.mark.pyshaft_api
def test_Create_importer_exporter():
    (
        api.request()
        .post(str(swagger_base_url) + "/v1/importer-exporter")
        .header("Content-Type", "application/json")
        .body({
          "eiName": "ABC Trading Co. test",
          "eiType": "1",
          "eiAddress": "123 Port Street, Alexandria test",
          "eiTaxnumber": "123456789",
          "eiNumber": "EI001 test",
          "eiCountriesId": "EG"
        })
        .prettify(verbose=False)
        .assert_status(201)
    )
    print("success created importer exporter with id", get_value("exporter_id"))


@pytest.mark.pyshaft_api
def test_Get_Importer_Exporter():
    importer_exporter_id = get_value("exporter_id")
    print(f"Using exporter_id from store: {importer_exporter_id}")
    (
        api.request()
        .get(str(swagger_base_url) + f"/v1/importer-exporter/{importer_exporter_id}")
        .assert_json_contains("$.id", "wharf random ")
        .assert_status(200)
    )
