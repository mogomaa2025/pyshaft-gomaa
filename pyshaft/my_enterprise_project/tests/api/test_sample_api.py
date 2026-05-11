import pytest
from pyshaft.api import ApiClient

@pytest.mark.pyshaft_api
def test_get_users(api: ApiClient):
    api.request().get('https://jsonplaceholder.typicode.com/users').assert_status(200)
