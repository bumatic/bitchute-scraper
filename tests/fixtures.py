"""
Shared test fixtures for BitChute scraper tests
"""

import pytest
from unittest.mock import Mock, MagicMock
import pandas as pd
from datetime import datetime


@pytest.fixture
def mock_video_data():
    """Create mock video data"""
    return {
        "video_id": "test123abc",
        "video_name": "Test Video Title",
        "description": "This is a test video description",
        "view_count": 1500,
        "duration": "10:30",
        "date_published": "2024-01-15T12:00:00Z",
        "thumbnail_url": "https://example.com/thumb.jpg",
        "category_id": "education",
        "sensitivity_id": "normal",
        "state_id": "published",
        "channel": {
            "channel_id": "ch123",
            "channel_name": "Test Channel"
        },
        "hashtags": [
            {"hashtag_id": "test", "hashtag_count": 100},
            {"hashtag_id": "example", "hashtag_count": 50}
        ],
        "is_short": False,
        "profile_id": "prof123"
    }


@pytest.fixture
def mock_channel_data():
    """Create mock channel data"""
    return {
        "channel_id": "ch123abc",
        "channel_name": "Test Channel",
        "description": "This is a test channel",
        "url_slug": "test-channel",
        "video_count": 150,
        "subscriber_count": "5.2K",
        "view_count": 250000,
        "date_created": "2022-01-01T00:00:00Z",
        "last_video_published": "2024-01-15T12:00:00Z",
        "profile_id": "prof123",
        "profile_name": "Test Profile",
        "category_id": "education",
        "sensitivity_id": "normal",
        "state_id": "active",
        "thumbnail_url": "https://example.com/channel_thumb.jpg",
        "membership_level": "Default",
        "is_verified": False,
        "is_subscribed": False,
        "show_adverts": True,
        "show_comments": True,
        "live_stream_enabled": False
    }


@pytest.fixture
def mock_hashtag_data():
    """Create mock hashtag data"""
    return {
        "hashtag_id": "test",
        "hashtag_count": 500
    }


@pytest.fixture
def mock_api_client():
    """Create mock API client"""
    from bitchute.core import BitChuteAPI
    
    client = Mock(spec=BitChuteAPI)
    client.verbose = False
    client.timeout = 30
    client.base_url = "https://api.bitchute.com/api"
    client.stats = {
        'requests_made': 0,
        'errors': 0,
        'cache_hits': 0,
        'last_request_time': 0
    }
    
    return client


@pytest.fixture
def mock_token_manager():
    """Create mock token manager"""
    from bitchute.token_manager import TokenManager
    
    manager = Mock(spec=TokenManager)
    manager.get_token.return_value = "test_token_123456789012345678"
    manager.has_valid_token.return_value = True
    manager.invalidate_token.return_value = None
    
    return manager


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame for testing"""
    return pd.DataFrame({
        'id': ['video1', 'video2', 'video3'],
        'title': ['Video 1', 'Video 2', 'Video 3'],
        'view_count': [1000, 2000, 3000],
        'channel_name': ['Channel A', 'Channel B', 'Channel A'],
        'duration': ['5:30', '10:15', '3:45'],
        'upload_date': ['2024-01-01', '2024-01-02', '2024-01-03'],
        'hashtags': [['#test'], ['#example', '#test'], ['#new']]
    })


@pytest.fixture
def mock_session():
    """Create mock requests session"""
    session = MagicMock()
    session.headers = {}
    return session


@pytest.fixture
def mock_successful_response():
    """Create mock successful API response"""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "videos": [],
        "channels": [],
        "hashtags": []
    }
    response.text = '{"success": true}'
    return response


@pytest.fixture
def mock_error_response():
    """Create mock error API response"""
    response = Mock()
    response.status_code = 500
    response.json.side_effect = ValueError("Invalid JSON")
    response.text = 'Internal Server Error'
    return response


@pytest.fixture
def temp_export_dir(tmp_path):
    """Create temporary directory for export tests"""
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    return export_dir


@pytest.fixture(autouse=True)
def reset_singleton_state():
    """Reset any singleton state between tests"""
    # Add any singleton resets here if needed
    yield
    # Cleanup after test


@pytest.fixture
def mock_webdriver():
    """Create mock webdriver for token extraction tests"""
    from selenium.webdriver import Chrome
    
    driver = Mock(spec=Chrome)
    driver.get.return_value = None
    driver.page_source = "<html><body>Test Page</body></html>"
    driver.execute_script.return_value = "test_token_123456789012345678"
    driver.quit.return_value = None
    
    return driver


# Fixture factories
def create_mock_video_data(video_id="test123", **kwargs):
    """Factory for creating mock video data with custom fields"""
    base_data = {
        "video_id": video_id,
        "video_name": f"Test Video {video_id}",
        "description": f"Description for {video_id}",
        "view_count": 1000,
        "duration": "5:00",
        "date_published": "2024-01-01T00:00:00Z",
        "channel": {
            "channel_id": "ch_default",
            "channel_name": "Default Channel"
        },
        "hashtags": []
    }
    base_data.update(kwargs)
    return base_data


def create_mock_channel_data(channel_id="ch123", **kwargs):
    """Factory for creating mock channel data with custom fields"""
    base_data = {
        "channel_id": channel_id,
        "channel_name": f"Channel {channel_id}",
        "description": f"Description for {channel_id}",
        "video_count": 50,
        "subscriber_count": "1K",
        "view_count": 50000
    }
    base_data.update(kwargs)
    return base_data


def create_mock_api_response(data_type="videos", items=None, **kwargs):
    """Factory for creating mock API responses"""
    if items is None:
        items = []
    
    response = {
        data_type: items,
        "success": True,
        "timestamp": datetime.utcnow().isoformat()
    }
    response.update(kwargs)
    return response