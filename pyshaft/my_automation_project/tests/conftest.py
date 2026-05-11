import pytest
from pyshaft.api import ApiClient

@pytest.fixture(scope='session')
def api():
    """Global API client fixture."""
    client = ApiClient()
    yield client

@pytest.fixture(scope='session')
def test_data():
    """Load environment or global test data."""
    return {'env': 'qa'}
