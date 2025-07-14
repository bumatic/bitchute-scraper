#!/usr/bin/env python3
"""
Test File Generator for BitChute API Scraper
Generates separate test files for each module in the refactored package
"""

import os
from pathlib import Path


def create_directory_structure():
    """Create the tests directory structure"""
    tests_dir = Path("tests")
    tests_dir.mkdir(exist_ok=True)
    
    # Create fixtures subdirectory
    fixtures_dir = tests_dir / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)
    
    return tests_dir, fixtures_dir


def generate_test_init(tests_dir):
    """Generate tests/__init__.py"""
    content = '''"""
BitChute API Scraper Test Suite
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import bitchute
test_dir = Path(__file__).parent
project_root = test_dir.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_DATA_DIR = test_dir / "fixtures"
'''
    
    with open(tests_dir / "__init__.py", "w") as f:
        f.write(content)
    print(f"✅ Generated {tests_dir / '__init__.py'}")


def generate_conftest(tests_dir):
    """Generate conftest.py with pytest fixtures"""
    content = '''"""
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
'''
    
    with open(tests_dir / "conftest.py", "w") as f:
        f.write(content)
    print(f"✅ Generated {tests_dir / 'conftest.py'}")


def generate_test_validators(tests_dir):
    """Generate test_validators.py"""
    content = '''"""
Tests for input validation functionality
"""

import pytest
from bitchute.validators import InputValidator
from bitchute.exceptions import ValidationError


class TestInputValidator:
    """Test input validation functionality"""
    
    def setup_method(self):
        self.validator = InputValidator()
    
    def test_validate_limit_valid(self):
        """Test valid limit validation"""
        self.validator.validate_limit(10)
        self.validator.validate_limit(50, max_limit=100)
        self.validator.validate_limit(1, min_limit=1)
        self.validator.validate_limit(100, max_limit=100)
    
    def test_validate_limit_invalid(self):
        """Test invalid limit validation"""
        with pytest.raises(ValidationError, match="Limit must be an integer"):
            self.validator.validate_limit("10")
        
        with pytest.raises(ValidationError, match="Limit must be at least"):
            self.validator.validate_limit(0)
        
        with pytest.raises(ValidationError, match="Limit must be at most"):
            self.validator.validate_limit(101, max_limit=100)
        
        with pytest.raises(ValidationError):
            self.validator.validate_limit(-5)
    
    def test_validate_offset(self):
        """Test offset validation"""
        self.validator.validate_offset(0)
        self.validator.validate_offset(100)
        self.validator.validate_offset(1000)
        
        with pytest.raises(ValidationError, match="Offset must be non-negative"):
            self.validator.validate_offset(-1)
        
        with pytest.raises(ValidationError, match="Offset must be an integer"):
            self.validator.validate_offset("0")
        
        with pytest.raises(ValidationError):
            self.validator.validate_offset(3.14)
    
    def test_validate_timeframe(self):
        """Test timeframe validation"""
        valid_timeframes = ['day', 'week', 'month']
        for timeframe in valid_timeframes:
            self.validator.validate_timeframe(timeframe)
        
        invalid_timeframes = ['year', 'hour', 'minute', 123, None, '']
        for timeframe in invalid_timeframes:
            with pytest.raises(ValidationError):
                self.validator.validate_timeframe(timeframe)
    
    def test_validate_search_query(self):
        """Test search query validation"""
        # Valid queries
        self.validator.validate_search_query("climate change")
        self.validator.validate_search_query("test")
        self.validator.validate_search_query("a" * 50)  # Max reasonable length
        
        # Invalid queries
        with pytest.raises(ValidationError, match="Query cannot be empty"):
            self.validator.validate_search_query("")
        
        with pytest.raises(ValidationError, match="Query cannot be empty"):
            self.validator.validate_search_query("   ")  # Only spaces
        
        with pytest.raises(ValidationError, match="Query too long"):
            self.validator.validate_search_query("a" * 101)
        
        with pytest.raises(ValidationError, match="Query must be a string"):
            self.validator.validate_search_query(123)
    
    def test_validate_video_id(self):
        """Test video ID validation"""
        # Valid video IDs
        valid_ids = [
            "CLrgZP4RWyly",
            "abc123def456",
            "test_video-123",
            "a" * 12  # Minimum length
        ]
        for video_id in valid_ids:
            self.validator.validate_video_id(video_id)
        
        # Invalid video IDs
        with pytest.raises(ValidationError, match="Video ID cannot be empty"):
            self.validator.validate_video_id("")
        
        with pytest.raises(ValidationError, match="Invalid video ID format"):
            self.validator.validate_video_id("abc")  # Too short
        
        with pytest.raises(ValidationError, match="Invalid video ID format"):
            self.validator.validate_video_id("a" * 25)  # Too long
        
        with pytest.raises(ValidationError, match="Invalid video ID format"):
            self.validator.validate_video_id("abc@123")  # Invalid characters
'''
    
    with open(tests_dir / "test_validators.py", "w") as f:
        f.write(content)
    print(f"✅ Generated {tests_dir / 'test_validators.py'}")


def generate_test_models(tests_dir):
    """Generate test_models.py"""
    content = '''"""
Tests for data models
"""

import pytest
from datetime import datetime
from bitchute.models import Video, Channel, Hashtag


class TestVideoModel:
    """Test Video data model"""
    
    def test_video_basic_properties(self):
        """Test basic video properties"""
        video = Video(
            id="test123",
            title="Test Video",
            view_count=1000,
            like_count=100,
            dislike_count=10,
            duration="10:30"
        )
        
        assert video.id == "test123"
        assert video.title == "Test Video"
        assert video.view_count == 1000
        assert video.like_count == 100
        assert video.dislike_count == 10
        assert video.duration == "10:30"
    
    def test_video_computed_properties(self):
        """Test computed properties"""
        video = Video(
            view_count=1000,
            like_count=100,
            dislike_count=10,
            duration="10:30"
        )
        
        # Test engagement rate: (likes + dislikes) / views
        assert video.engagement_rate == 0.11
        
        # Test like ratio: likes / (likes + dislikes)
        assert abs(video.like_ratio - 0.909) < 0.01
        
        # Test duration conversion: 10:30 = 630 seconds
        assert video.duration_seconds == 630
    
    def test_video_edge_cases(self):
        """Test edge cases for video model"""
        # Zero values
        video = Video(view_count=0, like_count=0, dislike_count=0)
        assert video.engagement_rate == 0.0
        assert video.like_ratio == 0.0
        assert video.duration_seconds == 0
        
        # Empty duration
        video = Video(duration="")
        assert video.duration_seconds == 0
    
    def test_video_url_generation(self):
        """Test automatic URL generation"""
        video = Video(id="test123")
        assert video.video_url == "https://www.bitchute.com/video/test123/"
        
        # Test with empty ID
        video = Video(id="")
        assert video.video_url == ""


class TestChannelModel:
    """Test Channel data model"""
    
    def test_channel_basic_properties(self):
        """Test basic channel properties"""
        channel = Channel(
            id="channel123",
            name="Test Channel",
            video_count=50,
            subscriber_count="1.2K",
            view_count=100000
        )
        
        assert channel.id == "channel123"
        assert channel.name == "Test Channel"
        assert channel.video_count == 50
        assert channel.subscriber_count == "1.2K"
        assert channel.view_count == 100000
    
    def test_subscriber_count_parsing(self):
        """Test subscriber count parsing"""
        test_cases = [
            ("1.2K", 1200),
            ("500", 500),
            ("2.5M", 2500000),
            ("10k", 10000),  # Lowercase
            ("invalid", 0),
            ("", 0),
        ]
        
        for input_val, expected in test_cases:
            channel = Channel(subscriber_count=input_val)
            assert channel.subscriber_count_numeric == expected
    
    def test_channel_url_generation(self):
        """Test automatic channel URL generation"""
        channel = Channel(id="channel123")
        assert channel.channel_url == "https://www.bitchute.com/channel/channel123/"


class TestHashtagModel:
    """Test Hashtag data model"""
    
    def test_hashtag_basic_properties(self):
        """Test basic hashtag properties"""
        hashtag = Hashtag(name="test", rank=1)
        
        assert hashtag.name == "test"
        assert hashtag.rank == 1
    
    def test_hashtag_name_processing(self):
        """Test hashtag name processing"""
        # Test without # prefix
        hashtag = Hashtag(name="test")
        assert hashtag.clean_name == "test"
        assert hashtag.formatted_name == "#test"
        
        # Test with # prefix
        hashtag = Hashtag(name="#test")
        assert hashtag.clean_name == "test"
        assert hashtag.formatted_name == "#test"
    
    def test_hashtag_url_generation(self):
        """Test hashtag URL generation"""
        hashtag = Hashtag(name="test")
        assert hashtag.url == "https://www.bitchute.com/hashtag/test/"
        
        hashtag = Hashtag(name="#test")
        assert hashtag.url == "https://www.bitchute.com/hashtag/test/"
'''
    
    with open(tests_dir / "test_models.py", "w") as f:
        f.write(content)
    print(f"✅ Generated {tests_dir / 'test_models.py'}")


def generate_test_core(tests_dir):
    """Generate test_core.py"""
    content = '''"""
Tests for core API functionality
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import requests

from bitchute.core import BitChuteAPI, SensitivityLevel, SortOrder
from bitchute.exceptions import BitChuteAPIError, ValidationError, RateLimitError


class TestBitChuteAPI:
    """Test main API functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Mock the token manager to avoid actual token extraction
        with patch('bitchute.core.TokenManager') as mock_token_manager:
            mock_token_manager.return_value.get_token.return_value = "mock_token"
            mock_token_manager.return_value.has_valid_token.return_value = True
            mock_token_manager.return_value.cleanup.return_value = None
            self.api = BitChuteAPI(verbose=False)
    
    def test_api_initialization(self):
        """Test API initialization"""
        assert self.api is not None
        assert self.api.verbose is False
        assert hasattr(self.api, 'session')
        assert hasattr(self.api, 'validator')
        assert hasattr(self.api, 'data_processor')
    
    @patch('requests.Session.post')
    def test_get_trending_videos_success(self, mock_post, mock_api_response):
        """Test successful trending videos request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_post.return_value = mock_response
        
        df = self.api.get_trending_videos('day', limit=2)
        
        assert len(df) == 2
        assert df.iloc[0]['id'] == 'video1'
        assert df.iloc[1]['id'] == 'video2'
        assert df.iloc[0]['view_count'] == 1000
        assert df.iloc[1]['view_count'] == 2000
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'beta/videos' in call_args[0][0]
        assert call_args[1]['json']['selection'] == 'trending-day'
        assert call_args[1]['json']['limit'] == 2
    
    @patch('requests.Session.post')
    def test_search_videos_success(self, mock_post, mock_api_response):
        """Test successful video search"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_post.return_value = mock_response
        
        df = self.api.search_videos('test query', limit=10)
        
        assert len(df) == 2
        call_args = mock_post.call_args
        assert 'beta/search/videos' in call_args[0][0]
        assert call_args[1]['json']['query'] == 'test query'
        assert call_args[1]['json']['limit'] == 10
    
    @patch('requests.Session.post')
    def test_api_error_handling(self, mock_post):
        """Test API error handling"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        with pytest.raises(BitChuteAPIError) as exc_info:
            self.api.get_trending_videos('day', limit=10)
        
        assert exc_info.value.status_code == 500
    
    @patch('requests.Session.post')
    def test_rate_limit_handling(self, mock_post):
        """Test rate limit error handling"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        
        with pytest.raises(RateLimitError):
            self.api.get_trending_videos('day', limit=10)
    
    def test_input_validation(self):
        """Test input validation in API methods"""
        # Test invalid timeframe
        with pytest.raises(ValidationError):
            self.api.get_trending_videos('invalid', limit=10)
        
        # Test invalid limit
        with pytest.raises(ValidationError):
            self.api.get_trending_videos('day', limit=0)
        
        # Test invalid search query
        with pytest.raises(ValidationError):
            self.api.search_videos('', limit=10)
'''
    
    with open(tests_dir / "test_core.py", "w") as f:
        f.write(content)
    print(f"✅ Generated {tests_dir / 'test_core.py'}")


def generate_test_utils(tests_dir):
    """Generate test_utils.py"""
    content = '''"""
Tests for utility functions
"""

import pytest
import pandas as pd
import time
import threading
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path

from bitchute.utils import (
    RateLimiter, DataProcessor, DataExporter, DataAnalyzer
)
from bitchute.models import Video, Channel, Hashtag


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    def test_rate_limiter_basic(self):
        """Test basic rate limiting"""
        limiter = RateLimiter(0.1)  # 100ms between requests
        
        start_time = time.time()
        limiter.wait()
        limiter.wait()
        end_time = time.time()
        
        # Should take at least 100ms
        assert end_time - start_time >= 0.09  # Small tolerance for timing


class TestDataProcessor:
    """Test data processing functions"""
    
    def setup_method(self):
        self.processor = DataProcessor()
    
    def test_parse_video_basic(self, mock_video_data):
        """Test basic video parsing"""
        video = self.processor.parse_video(mock_video_data)
        
        assert video.id == 'test123'
        assert video.title == 'Test Video'
        assert video.view_count == 1000
        assert video.channel_id == 'channel123'
        assert video.channel_name == 'Test Channel'
        assert video.hashtags == ['#test', '#video', '#example']
        assert video.video_url == 'https://www.bitchute.com/video/test123/'
    
    def test_parse_video_missing_fields(self):
        """Test video parsing with missing fields"""
        data = {'id': 'test123'}
        video = self.processor.parse_video(data)
        
        assert video.id == 'test123'
        assert video.title == ''
        assert video.view_count == 0
        assert video.hashtags == []
    
    def test_safe_int_conversion(self):
        """Test safe integer conversion"""
        assert self.processor._safe_int(100) == 100
        assert self.processor._safe_int('100') == 100
        assert self.processor._safe_int('100.5') == 100
        assert self.processor._safe_int(None) == 0
        assert self.processor._safe_int('invalid') == 0


class TestDataExporter:
    """Test data export functionality"""
    
    def test_export_csv(self, sample_dataframe):
        """Test CSV export"""
        exporter = DataExporter()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            filename = str(temp_path / "test")
            
            exported = exporter.export_data(sample_dataframe, filename, ['csv'])
            
            assert 'csv' in exported
            csv_file = Path(exported['csv'])
            assert csv_file.exists()
            
            # Verify content
            df_loaded = pd.read_csv(csv_file)
            assert len(df_loaded) == len(sample_dataframe)
            assert 'id' in df_loaded.columns


class TestDataAnalyzer:
    """Test data analysis functionality"""
    
    def test_analyze_videos_basic(self, sample_dataframe):
        """Test basic video analysis"""
        analyzer = DataAnalyzer()
        analysis = analyzer.analyze_videos(sample_dataframe)
        
        assert analysis['total_videos'] == 2
        assert 'views' in analysis
        assert analysis['views']['total'] == 3000  # 1000 + 2000
        assert analysis['views']['average'] == 1500
'''
    
    with open(tests_dir / "test_utils.py", "w") as f:
        f.write(content)
    print(f"✅ Generated {tests_dir / 'test_utils.py'}")


def generate_test_token_manager(tests_dir):
    """Generate test_token_manager.py"""
    content = '''"""
Tests for token management functionality
"""

import pytest
import time
import json
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path

from bitchute.token_manager import TokenManager
from bitchute.exceptions import TokenExtractionError


class TestTokenManager:
    """Test token management functionality"""
    
    def test_token_manager_init_no_cache(self):
        """Test token manager initialization without caching"""
        manager = TokenManager(cache_tokens=False, verbose=False)
        
        assert manager.cache_tokens == False
        assert manager.verbose == False
        assert manager.token is None
        assert manager.expires_at == 0
    
    def test_token_validation(self):
        """Test token validation logic"""
        manager = TokenManager(cache_tokens=False)
        
        # Valid tokens
        assert manager._is_valid_token("6t5eya4t4b4lwi3zjh6dxu6y9j6i")
        assert manager._is_valid_token("abc123def456")
        assert manager._is_valid_token("a" * 12)  # Minimum length
        
        # Invalid tokens
        assert not manager._is_valid_token("")
        assert not manager._is_valid_token("abc")  # Too short
        assert not manager._is_valid_token("a" * 101)  # Too long
        assert not manager._is_valid_token("abc@123")  # Invalid characters
        assert not manager._is_valid_token(None)
    
    def test_has_valid_token(self):
        """Test valid token checking"""
        manager = TokenManager(cache_tokens=False)
        
        # No token
        assert not manager.has_valid_token()
        
        # Expired token
        manager.token = "test_token"
        manager.expires_at = time.time() - 100  # Expired
        assert not manager.has_valid_token()
        
        # Valid token
        manager.expires_at = time.time() + 3600  # Valid for 1 hour
        assert manager.has_valid_token()
    
    @patch('bitchute.token_manager.webdriver.Chrome')
    def test_token_extraction_failure(self, mock_chrome):
        """Test token extraction failure handling"""
        mock_chrome.side_effect = Exception("WebDriver failed")
        
        manager = TokenManager(cache_tokens=False, verbose=False)
        
        with pytest.raises(TokenExtractionError):
            manager._create_webdriver()
    
    def test_token_extraction_from_source(self):
        """Test token extraction from page source"""
        manager = TokenManager(cache_tokens=False, verbose=False)
        
        # Test token patterns
        test_cases = [
            ('{"x-service-info": "token123"}', "token123"),
            ("x-service-info: 'token456'", "token456"),
            ('no token here', None),
        ]
        
        for page_source, expected_token in test_cases:
            result = manager._extract_token_from_source(page_source)
            assert result == expected_token
'''
    
    with open(tests_dir / "test_token_manager.py", "w") as f:
        f.write(content)
    print(f"✅ Generated {tests_dir / 'test_token_manager.py'}")


def generate_test_cli(tests_dir):
    """Generate test_cli.py"""
    content = '''"""
Tests for CLI functionality
"""

import pytest
import argparse
from unittest.mock import Mock, patch
import pandas as pd
from io import StringIO

from bitchute.cli import CLIFormatter, create_argument_parser


class TestCLIFormatter:
    """Test CLI formatting functionality"""
    
    def test_success_formatting(self):
        """Test success message formatting"""
        message = "Operation completed"
        formatted = CLIFormatter.success(message)
        
        assert "✅" in formatted
        assert message in formatted
        assert CLIFormatter.COLORS['green'] in formatted
        assert CLIFormatter.COLORS['end'] in formatted
    
    def test_error_formatting(self):
        """Test error message formatting"""
        message = "Operation failed"
        formatted = CLIFormatter.error(message)
        
        assert "❌" in formatted
        assert message in formatted
        assert CLIFormatter.COLORS['red'] in formatted
    
    def test_warning_formatting(self):
        """Test warning message formatting"""
        message = "Warning message"
        formatted = CLIFormatter.warning(message)
        
        assert "⚠️" in formatted
        assert message in formatted
        assert CLIFormatter.COLORS['yellow'] in formatted


class TestArgumentParser:
    """Test argument parser functionality"""
    
    def test_create_argument_parser(self):
        """Test argument parser creation"""
        parser = create_argument_parser()
        
        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.description is not None
    
    def test_trending_command_parsing(self):
        """Test trending command parsing"""
        parser = create_argument_parser()
        
        # Test basic trending command
        args = parser.parse_args(['trending'])
        assert args.command == 'trending'
        assert args.timeframe == 'day'  # default
        assert args.limit == 20  # default
        
        # Test with options
        args = parser.parse_args(['trending', '--timeframe', 'week', '--limit', '50'])
        assert args.timeframe == 'week'
        assert args.limit == 50
    
    def test_search_command_parsing(self):
        """Test search command parsing"""
        parser = create_argument_parser()
        
        args = parser.parse_args(['search', 'test query'])
        assert args.command == 'search'
        assert args.query == 'test query'
        assert args.limit == 50  # default
        assert args.sort == 'new'  # default
    
    def test_video_command_parsing(self):
        """Test video command parsing"""
        parser = create_argument_parser()
        
        args = parser.parse_args(['video', 'CLrgZP4RWyly'])
        assert args.command == 'video'
        assert args.video_id == 'CLrgZP4RWyly'
        assert args.counts == False  # default
        assert args.media == False  # default
        
        # Test with flags
        args = parser.parse_args(['video', 'CLrgZP4RWyly', '--counts', '--media'])
        assert args.counts == True
        assert args.media == True
'''

def generate_test_integration(tests_dir):
    """Generate test_integration.py"""
    content = '''"""
Integration tests for BitChute API scraper
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
import tempfile
from pathlib import Path

from bitchute.core import BitChuteAPI
from bitchute.utils import DataExporter
from bitchute.exceptions import BitChuteAPIError, ValidationError


class TestFullWorkflow:
    """Test complete workflows"""
    
    @patch('bitchute.core.TokenManager')
    @patch('requests.Session.post')
    def test_complete_trending_workflow(self, mock_post, mock_token_manager):
        """Test complete workflow from API creation to data export"""
        # Mock token manager
        mock_token_manager.return_value.get_token.return_value = "mock_token"
        mock_token_manager.return_value.has_valid_token.return_value = True
        mock_token_manager.return_value.cleanup.return_value = None
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'videos': [
                {
                    'id': 'workflow1',
                    'title': 'Workflow Test Video',
                    'view_count': 1000,
                    'duration': '5:30',
                    'uploader': {'id': 'wch1', 'name': 'Workflow Channel'},
                    'hashtags': ['workflow', 'test']
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Test complete workflow
        with BitChuteAPI(verbose=False) as api:
            # Get trending videos
            df = api.get_trending_videos('day', limit=10)
            
            # Verify data
            assert len(df) == 1
            assert df.iloc[0]['id'] == 'workflow1'
            assert df.iloc[0]['title'] == 'Workflow Test Video'
            
            # Export data
            with tempfile.TemporaryDirectory() as temp_dir:
                filename = str(Path(temp_dir) / "workflow_test")
                exporter = DataExporter()
                exported = exporter.export_data(df, filename, ['csv', 'json'])
                
                assert 'csv' in exported
                assert 'json' in exported
                assert Path(exported['csv']).exists()
                assert Path(exported['json']).exists()
            
            # Check API stats
            stats = api.get_api_stats()
            assert stats['requests_made'] > 0
            assert isinstance(stats['error_rate'], float)
    
    @patch('bitchute.core.TokenManager')
    def test_error_handling_workflow(self, mock_token_manager):
        """Test error handling in complete workflow"""
        # Mock token manager
        mock_token_manager.return_value.get_token.return_value = "mock_token"
        mock_token_manager.return_value.has_valid_token.return_value = True
        mock_token_manager.return_value.cleanup.return_value = None
        
        with BitChuteAPI(verbose=False) as api:
            # Test validation errors
            with pytest.raises(ValidationError):
                api.get_trending_videos('invalid_timeframe')
            
            with pytest.raises(ValidationError):
                api.search_videos('')  # Empty query
            
            with pytest.raises(ValidationError):
                api.get_video_details('')  # Empty video ID


class TestDataExportIntegration:
    """Test data export integration"""
    
    def test_export_multiple_formats(self, sample_dataframe):
        """Test exporting data to multiple formats"""
        exporter = DataExporter()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filename = str(Path(temp_dir) / "integration_test")
            
            exported = exporter.export_data(
                sample_dataframe,
                filename,
                ['csv', 'json']
            )
            
            # Verify files were created
            assert 'csv' in exported
            assert 'json' in exported
            
            csv_file = Path(exported['csv'])
            json_file = Path(exported['json'])
            
            assert csv_file.exists()
            assert json_file.exists()
            
            # Verify file contents
            df_from_csv = pd.read_csv(csv_file)
            assert len(df_from_csv) == len(sample_dataframe)
            assert set(df_from_csv.columns) == set(sample_dataframe.columns)
'''
    
    with open(tests_dir / "test_integration.py", "w") as f:
        f.write(content)
    print(f"✅ Generated {tests_dir / 'test_integration.py'}")

def generate_run_tests_script():
    """Generate run_tests.py script"""
    content = '''#!/usr/bin/env python3
"""
Test runner script for BitChute API scraper
"""

import subprocess
import sys
from pathlib import Path

def run_tests():
    """Run all tests with coverage"""
    test_dir = Path(__file__).parent / "tests"
    
    if not test_dir.exists():
        print("❌ Tests directory not found!")
        return 1
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_dir),
        "-v",
        "--cov=bitchute",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=85"
    ]
    
    print("🧪 Running tests with coverage...")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("✅ All tests passed!")
        print("📊 Coverage report generated in htmlcov/")
    else:
        print("❌ Some tests failed!")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())
'''
    
    with open("run_tests.py", "w") as f:
        f.write(content)
    print("✅ Generated run_tests.py")


def generate_pytest_ini():
    """Generate pytest.ini configuration file"""
    content = '''[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --strict-config
    --tb=short
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    api: marks tests that require API access
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
'''
    
    with open("pytest.ini", "w") as f:
        f.write(content)
    print("✅ Generated pytest.ini")


def generate_requirements_test():
    """Generate requirements-test.txt"""
    content = '''# Test dependencies for BitChute API scraper
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
pytest-asyncio>=0.20.0
coverage>=6.0.0
'''
    
    with open("requirements-test.txt", "w") as f:
        f.write(content)
    print("✅ Generated requirements-test.txt")

def main():
    """Generate all test files"""
    print("🧪 Generating BitChute API Scraper Test Suite...")
    
    # Create directory structure
    tests_dir, fixtures_dir = create_directory_structure()
    print(f"📁 Created test directories: {tests_dir}, {fixtures_dir}")
    
    # Generate test files
    test_generators = [
        ("__init__.py", generate_test_init),
        ("conftest.py", generate_conftest),
        ("test_validators.py", generate_test_validators),
        ("test_models.py", generate_test_models),
        ("test_core.py", generate_test_core),
        ("test_utils.py", generate_test_utils),
        ("test_token_manager.py", generate_test_token_manager),
        ("test_cli.py", generate_test_cli),
        ("test_integration.py", generate_test_integration),
    ]
    
    print("\n📝 Generating test files...")
    for filename, generator in test_generators:
        try:
            generator(tests_dir)
        except Exception as e:
            print(f"❌ Failed to generate {filename}: {e}")
    
    # Generate fixtures
    print("\n📦 Generating test fixtures...")
    try:
        generate_fixtures(fixtures_dir)
    except Exception as e:
        print(f"❌ Failed to generate fixtures: {e}")
    
    # Generate configuration files in project root
    print("\n⚙️ Generating configuration files...")
    config_generators = [
        ("run_tests.py", generate_run_tests_script),
        ("pytest.ini", generate_pytest_ini),
        ("requirements-test.txt", generate_requirements_test),
    ]
    
    for filename, generator in config_generators:
        try:
            generator()
        except Exception as e:
            print(f"❌ Failed to generate {filename}: {e}")
    
    print("\n🎉 Test suite generation complete!")
    print("\n📁 Generated structure:")
    print("├── tests/")
    print("│   ├── __init__.py")
    print("│   ├── conftest.py")
    print("│   ├── test_validators.py")
    print("│   ├── test_models.py") 
    print("│   ├── test_core.py")
    print("│   ├── test_utils.py")
    print("│   ├── test_token_manager.py")
    print("│   ├── test_cli.py")
    print("│   ├── test_integration.py")
    print("│   └── fixtures/")
    print("│       ├── mock_api_responses.json")
    print("│       ├── mock_video_data.json")
    print("│       └── mock_channel_data.json")
    print("├── run_tests.py")
    print("├── pytest.ini")
    print("└── requirements-test.txt")
    
    print("\n🚀 To run tests:")
    print("   python run_tests.py")
    print("   # or")
    print("   pytest tests/ -v --cov=bitchute")
    
    print("\n📋 To install test dependencies:")
    print("   pip install -r requirements-test.txt")
    
    # Verify all files were created
    print("\n🔍 Verifying generated files...")
    expected_files = [
        "tests/__init__.py",
        "tests/conftest.py", 
        "tests/test_validators.py",
        "tests/test_models.py",
        "tests/test_core.py",
        "tests/test_utils.py",
        "tests/test_token_manager.py",
        "tests/test_cli.py",
        "tests/test_integration.py",
        "tests/fixtures/mock_api_responses.json",
        "tests/fixtures/mock_video_data.json",
        "tests/fixtures/mock_channel_data.json",
        "run_tests.py",
        "pytest.ini",
        "requirements-test.txt"
    ]
    
    missing_files = []
    for file_path in expected_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("⚠️  Missing files:")
        for file_path in missing_files:
            print(f"   ❌ {file_path}")
    else:
        print("✅ All files generated successfully!")



if __name__ == "__main__":
    main()