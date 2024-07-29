from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from cf_speedtest import speedtest


@pytest.fixture
def mock_requests_session():
    with patch('cf_speedtest.speedtest.REQ_SESSION') as mock_session:
        yield mock_session


def test_get_our_country(mock_requests_session):
    mock_response = MagicMock()
    mock_response.text = 'loc=GB\nother=value'
    mock_requests_session.get.return_value = mock_response

    assert speedtest.get_our_country() == 'GB'


def test_preamble_unit(mock_requests_session):
    mock_response = MagicMock()
    mock_response.headers = {
        'cf-meta-ip': '1.2.3.4',
        'cf-meta-colo': 'LAX',
    }
    mock_requests_session.get.return_value = mock_response

    with patch('cf_speedtest.speedtest.get_our_country', return_value='US'):
        result = speedtest.preamble(False)
        assert '1.2.3.4' in result
        assert 'LAX' in result
        assert 'US' in result
