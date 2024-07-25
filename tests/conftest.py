from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def mock_time():
    with patch('cf_speedtest.speedtest.time') as mock_time:
        mock_time.time.return_value = 1234567890.0
        yield mock_time


@pytest.fixture
def mock_requests_session():
    with patch('cf_speedtest.speedtest.REQ_SESSION') as mock_session:
        yield mock_session
