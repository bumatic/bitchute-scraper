"""
Pytest configuration and shared fixtures
"""

import pytest
import json
from unittest.mock import Mock, patch
from pathlib import Path

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_video_data():
    """Mock video data for testing"""
    return {
        'id': 'test123',
        'title': 'Test Video',
        'description': 'Test description for video',
        'view_count': 1000,
        'like_count': 100,
        'dislike_count': 10,
        'duration': '10:30',
        'uploader': {
            'id': 'channel123',
            'name': 'Test Channel'
        },
        'hashtags': ['test', 'video', 'example'],
        'category': 'Education',
        'sensitivity': 'normal',
        'is_short': False,
        'upload_date': '2024-01-01T00:00:00Z',
        'thumbnail_url': 'https://example.com/thumb.jpg',
        'created_at': '2024-01-01T00:00:00Z'
    }


@pytest.fixture
def mock_channel_data():
    """Mock channel data for testing"""
    return {
        'id': 'channel123',
        'name': 'Test Channel',
        'title': 'Test Channel',  # Alternative name field
        'description': 'Test channel description',
        'video_count': 50,
        'subscriber_count': '1.2K',
        'view_count': 100000,
        'created_at': '2023-01-01T00:00:00Z',
        'category': 'Education',
        'thumbnail_url': 'https://example.com/channel.jpg',
        'is_verified': True
    }


@pytest.fixture
def mock_hashtag_data():
    """Mock hashtag data for testing"""
    return {
        'name': 'test',
        'video_count': 150,
        'rank': 1
    }


@pytest.fixture
def mock_api_response():
    """Mock API response structure"""
    return {
        'videos': [
            {
                'id': 'video1',
                'title': 'Video 1',
                'view_count': 1000,
                'duration': '5:30',
                'uploader': {'id': 'ch1', 'name': 'Channel 1'},
                'hashtags': ['tag1', 'tag2']
            },
            {
                'id': 'video2', 
                'title': 'Video 2',
                'view_count': 2000,
                'duration': '12:45',
                'uploader': {'id': 'ch2', 'name': 'Channel 2'},
                'hashtags': ['tag3', 'tag4']
            }
        ]
    }


@pytest.fixture
def mock_channels_response():
    """Mock channels API response"""
    return {
        'channels': [
            {
                'id': 'channel1',
                'name': 'Channel 1',
                'video_count': 25,
                'subscriber_count': '500',
                'view_count': 50000
            },
            {
                'id': 'channel2',
                'name': 'Channel 2', 
                'video_count': 75,
                'subscriber_count': '2.1K',
                'view_count': 150000
            }
        ]
    }


@pytest.fixture
def mock_hashtags_response():
    """Mock hashtags API response"""
    return {
        'hashtags': [
            {'name': 'trending1'},
            {'name': 'trending2'},
            {'name': 'trending3'}
        ]
    }


@pytest.fixture
def mock_token_manager():
    """Mock token manager"""
    with patch('bitchute.core.TokenManager') as mock:
        mock.return_value.get_token.return_value = "mock_token_12345"
        mock.return_value.has_valid_token.return_value = True
        mock.return_value.cleanup.return_value = None
        yield mock.return_value


@pytest.fixture
def sample_dataframe():
    """Sample DataFrame for testing"""
    import pandas as pd
    return pd.DataFrame([
        {
            'id': 'video1',
            'title': 'Test Video 1',
            'view_count': 1000,
            'channel_name': 'Channel 1',
            'duration': '5:30'
        },
        {
            'id': 'video2',
            'title': 'Test Video 2', 
            'view_count': 2000,
            'channel_name': 'Channel 2',
            'duration': '10:15'
        }
    ])
