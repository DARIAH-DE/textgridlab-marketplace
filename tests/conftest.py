import pytest
from marketplace import mp

@pytest.fixture
def app():
    return mp

