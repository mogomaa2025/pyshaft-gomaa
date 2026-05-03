import random

import pytest
from pyshaft import api, get_value

swagger_base_url = "http://10.9.100.170:8090/EWebService-web"


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
        .assert_json("$.statusCode", 201)
        .assert_json("$.message", "تم الحفظ بنجاح")
        .assert_json("$.success", True)
        .extract_json("$.data", "exporter_id")
    )
    print("success created importer exporter with id", get_value("exporter_id"))


@pytest.mark.pyshaft_api
def test_Get_Importer_Exporter():
    importer_exporter_id = get_value("exporter_id")
    print(f"Using exporter_id from store: {importer_exporter_id}")
    (
        api.request()
        .get(str(swagger_base_url) + f"/v1/importer-exporter/{importer_exporter_id}")
        .prettify(verbose=True)
        .assert_status(200)
        .assert_json("$.statusCode", 200)
        .assert_json("$.success", True)
        .assert_json("$.message", "Success")          # english message should be arabic
        .assert_json("$.data.id", importer_exporter_id)
    )


@pytest.mark.pyshaft_api
def test_Delete_importer_exporter():
    importer_exporter_id = get_value("exporter_id")
    print(f"Using exporter_id from store: {importer_exporter_id}")
    (
        api.request()
        .delete(str(swagger_base_url) + f"/v1/importer-exporter/{importer_exporter_id}")
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
        .assert_status(200)
       # .assert_json("$.statusCode", 200)
        .assert_json("$.success", True)
    )



@pytest.mark.pyshaft_api
def test_Delete_importer_exporter_again():
    importer_exporter_id = get_value("exporter_id")
    print(f"Using exporter_id from store: {importer_exporter_id}")
    (
        api.request()
        .delete(str(swagger_base_url) + f"/v1/importer-exporter/{importer_exporter_id}")
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
        .assert_status(404)
    )











@pytest.mark.pyshaft_api
def test_Get_All_Importer_Exporter():
    importer_exporter_id = get_value("exporter_id")
    print(f"Using exporter_id from store: {importer_exporter_id}")
    (
        api.request()
        .get(str(swagger_base_url) + f"/v1/importer-exporter")
        .prettify(verbose=True)
      #  .assert_json("$.data.id", importer_exporter_id)
        .assert_status(200)
    )

@pytest.mark.pyshaft_api
def test_Get_filtered_and_paginated():
    importer_exporter_id = get_value("exporter_id")
    print(f"Using exporter_id from store: {importer_exporter_id}")
    (
        api.request()
        .get(str(swagger_base_url) + f"/v1/importer-exporter?filtered=eyJpZCI6MTE0fQ==")
        .prettify(verbose=True)
        .assert_status(200)
        .assert_json("$.statusCode", 200)
    )