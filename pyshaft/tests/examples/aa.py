import pytest

from pyshaft import api as a, pipeline, get_value

body = {
    "name": "Max",
    "species": "DOG",
    "breed": "Golden Retriever",
    "ageMonths": 24,
    "size": "LARGE",
    "color": "Golden",
    "gender": "MALE",
    "goodWithKids": True,
    "price": "250.00",
    "currency": "USD",
    "status": "AVAILABLE",
    "description": "Friendly golden retriever looking for an active family",
    "medicalInfo": {
        "vaccinated": True,
        "spayedNeutered": True,
        "microchipped": True,
        "specialNeeds": False,
        "healthNotes": "Up to date on all vaccinations"
    }
}
Bearer_Token = ""
@pytest.mark.pyshaft_api
def test_aa():
    (
    a.request()
    .post("https://api.petstoreapi.com/v1/pets")
    .header("Content-Type", "application/json")
    .header("Authorization", "Bearer "+Bearer_Token+"")
    .body(body)
    .prettify()
    .extract_json("$data._id", "unicorn_id")
    .assert_status(201)
    )
    pipeline.set("unicorn_id", a.stored("unicorn_id")) # SET


def test_bb():
    unicorn_id = get_value("unicorn_id") # GET
    (
    a.request()
    .delete(str("https://crudcrud.com/api/a8b4d4d3ed39421a96e6b1a64ff37459/unicorns/"+unicorn_id+""))
    .header("Content-Type", "application/json")
    .body(body)
    .prettify()
    .assert_status(201)
    )



