"""
Shared test configuration and fixtures for BitChute scraper tests.

This file contains shared fixtures and configuration that can be used
across all test modules in the tests/ directory.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock
import pandas as pd

from bitchute.core import BitChuteAPI


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def sample_video_data():
    """Sample video data for testing."""
    return pd.DataFrame([
        {
            'id': 'video123',
            'title': 'Sample Video 1',
            'view_count': 1500,
            'like_count': 50,
            'dislike_count': 5,
            'channel_name': 'Test Channel',
            'duration': '12:34',
            'upload_date': '2024-01-15',
            'local_thumbnail_path': '',
            'local_video_path': ''
        },
        {
            'id': 'video456', 
            'title': 'Sample Video 2',
            'view_count': 2300,
            'like_count': 75,
            'dislike_count': 8,
            'channel_name': 'News Channel',
            'duration': '8:45',
            'upload_date': '2024-01-16',
            'local_thumbnail_path': '',
            'local_video_path': ''
        }
    ])


@pytest.fixture
def sample_channel_data():
    """Sample channel data for testing."""
    return pd.DataFrame([
        {
            'id': 'channel123',
            'name': 'Test Channel',
            'video_count': 50,
            'subscriber_count': '1.2K',
            'view_count': 75000,
            'created_date': '2024-01-01'
        }
    ])


@pytest.fixture
def mock_requests_response():
    """Mock requests response for download tests."""
    response = Mock()
    response.status_code = 200
    response.headers = {'content-length': '1024'}
    response.iter_content.return_value = [b'test data chunk'] * 5
    return response


# Configure pytest settings
def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "cli: marks tests as CLI tests"
    )
    config.addinivalue_line(
        "markers", "download: marks tests as download tests"
    )