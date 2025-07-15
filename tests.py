"""
Comprehensive test suite for BitChute API scraper
"""

import pytest
import pandas as pd
import json
import time
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict
from datetime import datetime

# Test imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bitchute.core import BitChuteAPI, SensitivityLevel, SortOrder, VideoSelection
from bitchute.models import Video, Channel, Hashtag, APIStats
from bitchute.exceptions import (
    BitChuteAPIError, TokenExtractionError, RateLimitError, 
    ValidationError, NetworkError
)
from bitchute.token_manager import TokenManager
from bitchute.validators import InputValidator
from bitchute.utils import (
    DataProcessor, RateLimiter, RequestBuilder, 
    DataExporter, DataAnalyzer, ContentFilter
)


class TestBitChuteAPI:
    """Test BitChute API core functionality"""
    
    @pytest.fixture
    def api_client(self):
        """Create API client for testing"""
        return BitChuteAPI(verbose=False, cache_tokens=False)
    
    @pytest.fixture
    def mock_response_data(self):
        """Mock API response data"""
        return {
            "videos": [
                {
                    "video_id": "test123",
                    "video_name": "Test Video",
                    "description": "Test description",
                    "view_count": 1000,
                    "duration": "5:30",
                    "date_published": "2024-01-01",
                    "thumbnail_url": "https://example.com/thumb.jpg",
                    "category_id": "news",
                    "sensitivity_id": "normal",
                    "state_id": "published",
                    "channel": {
                        "channel_id": "ch123",
                        "channel_name": "Test Channel"
                    },
                    "hashtags": [
                        {"hashtag_id": "test", "hashtag_count": 100}
                    ]
                }
            ]
        }
    
    @pytest.fixture
    def mock_token_manager(self):
        """Mock token manager"""
        manager = Mock(spec=TokenManager)
        manager.get_token.return_value = "test_token_123456789012345678"
        manager.has_valid_token.return_value = True
        return manager
    
    def test_api_initialization(self):
        """Test API client initialization"""
        api = BitChuteAPI(verbose=True, rate_limit=1.0, timeout=60)
        
        assert api.verbose == True
        assert api.timeout == 60
        assert api.base_url == "https://api.bitchute.com/api"
        assert hasattr(api, 'session')
        assert hasattr(api, 'token_manager')
        assert hasattr(api, 'validator')
    
    def test_session_headers(self, api_client):
        """Test session headers are properly set"""
        headers = api_client.session.headers
        
        assert 'accept' in headers
        assert 'content-type' in headers
        assert 'origin' in headers
        assert 'referer' in headers
        assert 'user-agent' in headers
    
    @patch('bitchute.core.requests.Session.post')
    def test_make_request_success(self, mock_post, api_client, mock_response_data):
        """Test successful API request"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response
        
        # Mock token manager
        api_client.token_manager = Mock()
        api_client.token_manager.get_token.return_value = "test_token"
        
        result = api_client._make_request("beta/videos", {"limit": 10})
        
        assert result == mock_response_data
        mock_post.assert_called_once()
    
    @patch('bitchute.core.requests.Session.post')
    def test_make_request_rate_limit(self, mock_post, api_client):
        """Test rate limit handling"""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        
        api_client.token_manager = Mock()
        api_client.token_manager.get_token.return_value = "test_token"
        
        with pytest.raises(RateLimitError):
            api_client._make_request("beta/videos", {"limit": 10})
    
    @patch('bitchute.core.requests.Session.post')
    def test_make_request_api_error(self, mock_post, api_client):
        """Test API error handling"""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        api_client.token_manager = Mock()
        api_client.token_manager.get_token.return_value = "test_token"
        
        with pytest.raises(BitChuteAPIError):
            api_client._make_request("beta/videos", {"limit": 10})
    
    def test_get_trending_videos_validation(self, api_client):
        """Test input validation for trending videos"""
        # Test invalid timeframe
        with pytest.raises(ValidationError):
            api_client.get_trending_videos("invalid")
        
        # Test invalid limit
        with pytest.raises(ValidationError):
            api_client.get_trending_videos("day", limit=0)
        
        # Test invalid per_page
        with pytest.raises(ValidationError):
            api_client.get_trending_videos("day", per_page=150)
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_get_trending_videos_success(self, mock_request, api_client, mock_response_data):
        """Test successful trending videos retrieval"""
        mock_request.return_value = mock_response_data
        
        result = api_client.get_trending_videos("day", limit=1)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert 'id' in result.columns
        assert 'title' in result.columns
        assert 'view_count' in result.columns
        
        # Check data content
        assert result.iloc[0]['id'] == "test123"
        assert result.iloc[0]['title'] == "Test Video"
        assert result.iloc[0]['view_count'] == 1000
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_get_trending_videos_empty_response(self, mock_request, api_client):
        """Test handling of empty API response"""
        mock_request.return_value = {"videos": []}
        
        result = api_client.get_trending_videos("day", limit=10)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_search_videos_success(self, mock_request, api_client, mock_response_data):
        """Test successful video search"""
        mock_request.return_value = mock_response_data
        
        result = api_client.search_videos("test query", limit=1)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        mock_request.assert_called_with(
            "beta/search/videos",
            {
                "offset": 0,
                "limit": 1,
                "query": "test query",
                "sensitivity_id": "normal",
                "sort": "new"
            }
        )
    
    def test_search_videos_validation(self, api_client):
        """Test search validation"""
        # Test empty query
        with pytest.raises(ValidationError):
            api_client.search_videos("")
        
        # Test invalid sensitivity
        with pytest.raises(ValidationError):
            api_client.search_videos("test", sensitivity="invalid")
        
        # Test invalid sort order
        with pytest.raises(ValidationError):
            api_client.search_videos("test", sort="invalid")
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_get_video_details_success(self, mock_request, api_client):
        """Test successful video details retrieval"""
        mock_video_data = {
            "video_id": "test123",
            "video_name": "Test Video",
            "description": "Test description",
            "view_count": 1000,
            "duration": "5:30",
            "date_published": "2024-01-01",
            "channel": {
                "channel_id": "ch123",
                "channel_name": "Test Channel"
            }
        }
        
        mock_counts_data = {
            "like_count": 50,
            "dislike_count": 5,
            "view_count": 1100
        }
        
        # Mock multiple API calls
        mock_request.side_effect = [mock_video_data, mock_counts_data]
        
        result = api_client.get_video_details("test123", include_counts=True)
        
        assert isinstance(result, Video)
        assert result.id == "test123"
        assert result.title == "Test Video"
        assert result.like_count == 50
        assert result.dislike_count == 5
        assert result.view_count == 1100  # Updated from counts
    
    def test_get_video_details_validation(self, api_client):
        """Test video details validation"""
        # Test invalid video ID
        with pytest.raises(ValidationError):
            api_client.get_video_details("")
        
        with pytest.raises(ValidationError):
            api_client.get_video_details("invalid-id-format")
    
    def test_get_api_stats(self, api_client):
        """Test API statistics retrieval"""
        # Make some requests to generate stats
        api_client.stats['requests_made'] = 10
        api_client.stats['errors'] = 1
        api_client.stats['last_request_time'] = time.time()
        
        stats = api_client.get_api_stats()
        
        assert isinstance(stats, dict)
        assert 'requests_made' in stats
        assert 'errors' in stats
        assert 'error_rate' in stats
        assert stats['requests_made'] == 10
        assert stats['errors'] == 1
        assert stats['error_rate'] == 0.1


class TestDataModels:
    """Test data models"""
    
    def test_video_model_initialization(self):
        """Test Video model initialization"""
        video = Video(
            id="test123",
            title="Test Video",
            view_count=1000,
            duration="5:30"
        )
        
        assert video.id == "test123"
        assert video.title == "Test Video"
        assert video.view_count == 1000
        assert video.duration == "5:30"
        assert video.scrape_timestamp > 0
    
    def test_video_computed_properties(self):
        """Test Video computed properties"""
        video = Video(
            id="test123",
            view_count=1000,
            like_count=100,
            dislike_count=20,
            duration="5:30"
        )
        
        assert video.engagement_rate == 0.12  # (100 + 20) / 1000
        assert video.like_ratio == 100/120  # 100 / (100 + 20)
        assert video.duration_seconds == 330  # 5*60 + 30
    
    def test_channel_model_initialization(self):
        """Test Channel model initialization"""
        channel = Channel(
            id="ch123",
            name="Test Channel",
            video_count=50,
            subscriber_count="1.2K",
            view_count=100000
        )
        
        assert channel.id == "ch123"
        assert channel.name == "Test Channel"
        assert channel.video_count == 50
        assert channel.subscriber_count_numeric == 1200
        assert channel.average_views_per_video == 2000
    
    def test_hashtag_model_initialization(self):
        """Test Hashtag model initialization"""
        hashtag = Hashtag(
            name="test",
            rank=1,
            video_count=100
        )
        
        assert hashtag.name == "test"
        assert hashtag.clean_name == "test"
        assert hashtag.formatted_name == "#test"
        assert hashtag.rank == 1
        assert hashtag.video_count == 100


class TestValidators:
    """Test input validators"""
    
    def test_input_validator_initialization(self):
        """Test InputValidator initialization"""
        validator = InputValidator()
        
        assert hasattr(validator, 'VALID_TIMEFRAMES')
        assert hasattr(validator, 'VALID_SENSITIVITIES')
        assert hasattr(validator, 'VALID_SORT_ORDERS')
    
    def test_validate_limit(self):
        """Test limit validation"""
        validator = InputValidator()
        
        # Valid limits
        validator.validate_limit(50)
        validator.validate_limit(1)
        validator.validate_limit(100)
        
        # Invalid limits
        with pytest.raises(ValidationError):
            validator.validate_limit(0)
        
        with pytest.raises(ValidationError):
            validator.validate_limit(150)
        
        with pytest.raises(ValidationError):
            validator.validate_limit("invalid")
    
    def test_validate_timeframe(self):
        """Test timeframe validation"""
        validator = InputValidator()
        
        # Valid timeframes
        validator.validate_timeframe("day")
        validator.validate_timeframe("week")
        validator.validate_timeframe("month")
        
        # Invalid timeframes
        with pytest.raises(ValidationError):
            validator.validate_timeframe("invalid")
        
        with pytest.raises(ValidationError):
            validator.validate_timeframe(123)
    
    def test_validate_video_id(self):
        """Test video ID validation"""
        validator = InputValidator()
        
        # Valid video IDs
        validator.validate_video_id("test123abc")
        validator.validate_video_id("abcd1234_test")
        validator.validate_video_id("test-123_abc")
        
        # Invalid video IDs
        with pytest.raises(ValidationError):
            validator.validate_video_id("")
        
        with pytest.raises(ValidationError):
            validator.validate_video_id("ab")  # Too short
        
        with pytest.raises(ValidationError):
            validator.validate_video_id("test@123")  # Invalid characters
    
    def test_validate_search_query(self):
        """Test search query validation"""
        validator = InputValidator()
        
        # Valid queries
        validator.validate_search_query("test query")
        validator.validate_search_query("bitcoin")
        validator.validate_search_query("test 123")
        
        # Invalid queries
        with pytest.raises(ValidationError):
            validator.validate_search_query("")
        
        with pytest.raises(ValidationError):
            validator.validate_search_query("   ")
        
        with pytest.raises(ValidationError):
            validator.validate_search_query("a" * 101)  # Too long


class TestUtils:
    """Test utility functions"""
    
    def test_data_processor_parse_video(self):
        """Test DataProcessor video parsing"""
        processor = DataProcessor()
        
        video_data = {
            "video_id": "test123",
            "video_name": "Test Video",
            "description": "Test description",
            "view_count": 1000,
            "duration": "5:30",
            "date_published": "2024-01-01",
            "channel": {
                "channel_id": "ch123",
                "channel_name": "Test Channel"
            },
            "hashtags": [
                {"hashtag_id": "test", "hashtag_count": 100}
            ]
        }
        
        video = processor.parse_video(video_data)
        
        assert isinstance(video, Video)
        assert video.id == "test123"
        assert video.title == "Test Video"
        assert video.view_count == 1000
        assert video.channel_id == "ch123"
        assert video.channel_name == "Test Channel"
        assert "#test" in video.hashtags
    
    def test_data_processor_parse_channel(self):
        """Test DataProcessor channel parsing"""
        processor = DataProcessor()
        
        channel_data = {
            "channel_id": "ch123",
            "channel_name": "Test Channel",
            "description": "Test description",
            "video_count": 50,
            "subscriber_count": "1.2K",
            "view_count": 100000
        }
        
        channel = processor.parse_channel(channel_data)
        
        assert isinstance(channel, Channel)
        assert channel.id == "ch123"
        assert channel.name == "Test Channel"
        assert channel.video_count == 50
        assert channel.subscriber_count == "1.2K"
        assert channel.view_count == 100000
    
    def test_rate_limiter(self):
        """Test rate limiter functionality"""
        limiter = RateLimiter(rate_limit=0.1)  # 0.1 second limit
        
        start_time = time.time()
        limiter.wait()
        limiter.wait()
        end_time = time.time()
        
        # Should have waited at least 0.1 seconds
        assert end_time - start_time >= 0.1
    
    def test_data_exporter(self):
        """Test data export functionality"""
        exporter = DataExporter()
        
        # Create test DataFrame
        df = pd.DataFrame({
            'id': ['test1', 'test2'],
            'title': ['Video 1', 'Video 2'],
            'view_count': [1000, 2000]
        })
        
        # Test CSV export
        exported = exporter.export_data(df, 'test_export', ['csv'])
        
        assert 'csv' in exported
        assert exported['csv'].endswith('.csv')
        
        # Clean up
        if os.path.exists(exported['csv']):
            os.remove(exported['csv'])
    
    def test_data_analyzer(self):
        """Test data analysis functionality"""
        analyzer = DataAnalyzer()
        
        # Create test DataFrame
        df = pd.DataFrame({
            'id': ['test1', 'test2'],
            'title': ['Video 1', 'Video 2'],
            'view_count': [1000, 2000],
            'duration': ['5:30', '10:15'],
            'channel_name': ['Channel A', 'Channel B'],
            'hashtags': [['#test1', '#crypto'], ['#test2', '#bitcoin']]
        })
        
        analysis = analyzer.analyze_videos(df)
        
        assert isinstance(analysis, dict)
        assert 'total_videos' in analysis
        assert 'views' in analysis
        assert 'top_channels' in analysis
        assert 'duration' in analysis
        assert analysis['total_videos'] == 2
        assert analysis['views']['total'] == 3000
        assert analysis['views']['average'] == 1500
    
    def test_content_filter(self):
        """Test content filtering functionality"""
        filter_obj = ContentFilter()
        
        # Create test DataFrame
        df = pd.DataFrame({
            'id': ['test1', 'test2', 'test3'],
            'title': ['Bitcoin News', 'Crypto Update', 'Other Video'],
            'view_count': [500, 1500, 2500],
            'duration': ['2:30', '5:45', '15:20'],
            'channel_name': ['CryptoNews', 'BitcoinDaily', 'OtherChannel']
        })
        
        # Test view count filtering
        filtered = filter_obj.filter_by_views(df, min_views=1000)
        assert len(filtered) == 2
        assert all(filtered['view_count'] >= 1000)
        
        # Test keyword filtering
        filtered = filter_obj.filter_by_keywords(df, ['bitcoin', 'crypto'])
        assert len(filtered) == 2
        assert 'Other Video' not in filtered['title'].values
        
        # Test channel filtering
        filtered = filter_obj.filter_by_channel(df, ['CryptoNews'])
        assert len(filtered) == 1
        assert filtered.iloc[0]['channel_name'] == 'CryptoNews'


class TestTokenManager:
    """Test token management functionality"""
    
    def test_token_manager_initialization(self):
        """Test TokenManager initialization"""
        manager = TokenManager(cache_tokens=False, verbose=False)
        
        assert manager.cache_tokens == False
        assert manager.verbose == False
        assert manager.token is None
        assert manager.expires_at == 0
    
    def test_token_validation(self):
        """Test token validation"""
        manager = TokenManager(cache_tokens=False, verbose=False)
        
        # Valid tokens
        assert manager._is_valid_token("abcd1234efgh5678ijkl9012mnop")
        assert manager._is_valid_token("1234567890123456789012345678")
        assert manager._is_valid_token("test_token_123456789012345678")
        
        # Invalid tokens
        assert not manager._is_valid_token("")
        assert not manager._is_valid_token("too_short")
        assert not manager._is_valid_token("too_long_token_123456789012345678901234567890")
        assert not manager._is_valid_token("invalid@token#123456789012345678")
    
    @patch('bitchute.token_manager.requests.post')
    def test_timer_api_extraction(self, mock_post):
        """Test token extraction via timer API"""
        manager = TokenManager(cache_tokens=False, verbose=False)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = "test_token_123456789012345678"
        mock_post.return_value = mock_response
        
        token = manager._extract_token_via_timer_api()
        
        assert token == "test_token_123456789012345678"
        mock_post.assert_called_once()
    
    def test_token_generation(self):
        """Test token generation"""
        manager = TokenManager(cache_tokens=False, verbose=False)
        
        token = manager._generate_token()
        
        assert isinstance(token, str)
        assert len(token) == 28
        assert manager._is_valid_token(token)
    
    def test_token_caching(self):
        """Test token caching functionality"""
        manager = TokenManager(cache_tokens=True, verbose=False)
        
        # Set a token
        test_token = "test_token_123456789012345678"
        manager.token = test_token
        manager.expires_at = time.time() + 3600  # 1 hour from now
        
        # Save to cache
        manager._save_token_cache()
        
        # Create new manager and load from cache
        new_manager = TokenManager(cache_tokens=True, verbose=False)
        new_manager.cache_file = manager.cache_file
        new_manager._load_cached_token()
        
        assert new_manager.token == test_token
        assert new_manager.has_valid_token()
        
        # Clean up
        if manager.cache_file.exists():
            manager.cache_file.unlink()
    
    def test_token_invalidation(self):
        """Test token invalidation"""
        manager = TokenManager(cache_tokens=False, verbose=False)
        
        # Set a token
        manager.token = "test_token_123456789012345678"
        manager.expires_at = time.time() + 3600
        
        assert manager.has_valid_token()
        
        # Invalidate token
        manager.invalidate_token()
        
        assert manager.token is None
        assert manager.expires_at == 0
        assert not manager.has_valid_token()


class TestExceptions:
    """Test custom exceptions"""
    
    def test_bitchute_api_error(self):
        """Test BitChuteAPIError"""
        error = BitChuteAPIError("Test error", 500)
        
        assert str(error) == "BitChute API Error (500): Test error"
        assert error.status_code == 500
        assert error.message == "Test error"
    
    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError("Invalid input", "test_field")
        
        assert "test_field" in str(error)
        assert "Invalid input" in str(error)
        assert error.field == "test_field"
    
    def test_rate_limit_error(self):
        """Test RateLimitError"""
        error = RateLimitError()
        
        assert error.status_code == 429
        assert "Rate limit exceeded" in str(error)
    
    def test_token_extraction_error(self):
        """Test TokenExtractionError"""
        error = TokenExtractionError("Token extraction failed")
        
        assert "Token extraction failed" in str(error)


class TestIntegration:
    """Integration tests for the complete package"""
    
    @pytest.fixture
    def mock_api_responses(self):
        """Mock complete API responses for integration testing"""
        return {
            "videos": {
                "videos": [
                    {
                        "video_id": "test123",
                        "video_name": "Test Video 1",
                        "description": "Test description 1",
                        "view_count": 1000,
                        "duration": "5:30",
                        "date_published": "2024-01-01",
                        "thumbnail_url": "https://example.com/thumb1.jpg",
                        "category_id": "news",
                        "sensitivity_id": "normal",
                        "state_id": "published",
                        "channel": {
                            "channel_id": "ch123",
                            "channel_name": "Test Channel"
                        },
                        "hashtags": [{"hashtag_id": "test", "hashtag_count": 100}]
                    },
                    {
                        "video_id": "test456",
                        "video_name": "Test Video 2",
                        "description": "Test description 2",
                        "view_count": 2000,
                        "duration": "10:15",
                        "date_published": "2024-01-02",
                        "thumbnail_url": "https://example.com/thumb2.jpg",
                        "category_id": "education",
                        "sensitivity_id": "normal",
                        "state_id": "published",
                        "channel": {
                            "channel_id": "ch456",
                            "channel_name": "Education Channel"
                        },
                        "hashtags": [{"hashtag_id": "education", "hashtag_count": 200}]
                    }
                ]
            },
            "channels": {
                "channels": [
                    {
                        "channel_id": "ch123",
                        "channel_name": "Test Channel",
                        "description": "Test channel description",
                        "video_count": 50,
                        "subscriber_count": "1.2K",
                        "view_count": 100000
                    }
                ]
            },
            "hashtags": {
                "hashtags": [
                    {
                        "hashtag_id": "test",
                        "hashtag_count": 100
                    },
                    {
                        "hashtag_id": "education",
                        "hashtag_count": 200
                    }
                ]
            }
        }
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_full_workflow_trending_videos(self, mock_request, mock_api_responses):
        """Test complete workflow for trending videos"""
        mock_request.return_value = mock_api_responses["videos"]
        
        api = BitChuteAPI(verbose=False)
        
        # Get trending videos
        df = api.get_trending_videos("day", limit=2)
        
        # Verify DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert 'id' in df.columns
        assert 'title' in df.columns
        assert 'view_count' in df.columns
        assert 'channel_name' in df.columns
        
        # Verify data content
        assert df.iloc[0]['id'] == "test123"
        assert df.iloc[1]['id'] == "test456"
        assert df.iloc[0]['view_count'] == 1000
        assert df.iloc[1]['view_count'] == 2000
        
        # Test data analysis
        analyzer = DataAnalyzer()
        analysis = analyzer.analyze_videos(df)
        
        assert analysis['total_videos'] == 2
        assert analysis['views']['total'] == 3000
        assert analysis['views']['average'] == 1500
        
        # Test data filtering
        filter_obj = ContentFilter()
        filtered = filter_obj.filter_by_views(df, min_views=1500)
        assert len(filtered) == 1
        assert filtered.iloc[0]['id'] == "test456"
        
        # Test data export
        exporter = DataExporter()
        exported = exporter.export_data(df, 'test_integration', ['csv'])
        
        assert 'csv' in exported
        assert os.path.exists(exported['csv'])
        
        # Clean up
        os.remove(exported['csv'])
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_search_and_analysis_workflow(self, mock_request, mock_api_responses):
        """Test search and analysis workflow"""
        mock_request.return_value = mock_api_responses["videos"]
        
        api = BitChuteAPI(verbose=False)
        
        # Search videos
        df = api.search_videos("test query", limit=2)
        
        # Analyze results
        analyzer = DataAnalyzer()
        analysis = analyzer.analyze_videos(df)
        
        assert 'top_channels' in analysis
        assert 'top_hashtags' in analysis
        
        # Filter by channel
        filter_obj = ContentFilter()
        filtered = filter_obj.filter_by_channel(df, ['Test Channel'])
        
        assert len(filtered) == 1
        assert filtered.iloc[0]['channel_name'] == 'Test Channel'
    
    def test_error_handling_workflow(self):
        """Test error handling in complete workflow"""
        api = BitChuteAPI(verbose=False)
        
        # Test validation errors
        with pytest.raises(ValidationError):
            api.get_trending_videos("invalid_timeframe")
        
        with pytest.raises(ValidationError):
            api.search_videos("")
        
        with pytest.raises(ValidationError):
            api.get_video_details("invalid_id")
        
        # Test API stats after errors
        stats = api.get_api_stats()
        assert isinstance(stats, dict)
        assert 'error_rate' in stats


class TestPerformance:
    """Performance tests"""
    
    @pytest.mark.performance
    def test_large_dataset_handling(self):
        """Test handling of large datasets"""
        # Create large mock dataset
        large_data = {
            "videos": []
        }
        
        for i in range(1000):
            large_data["videos"].append({
                "video_id": f"test{i}",
                "video_name": f"Test Video {i}",
                "description": f"Description {i}",
                "view_count": i * 100,
                "duration": "5:30",
                "date_published": "2024-01-01",
                "channel": {
                    "channel_id": f"ch{i}",
                    "channel_name": f"Channel {i}"
                },
                "hashtags": [{"hashtag_id": f"tag{i}", "hashtag_count": i}]
            })
        
        processor = DataProcessor()
        
        start_time = time.time()
        videos = [processor.parse_video(data) for data in large_data["videos"]]
        processing_time = time.time() - start_time
        
        assert len(videos) == 1000
        assert processing_time < 5.0  # Should process 1000 videos in under 5 seconds
    
    @pytest.mark.performance
    def test_concurrent_requests_simulation(self):
        """Test concurrent request handling simulation"""
        rate_limiter = RateLimiter(rate_limit=0.01)  # Very fast rate limit
        
        start_time = time.time()
        
        # Simulate 10 concurrent requests
        for _ in range(10):
            rate_limiter.wait()
        
        total_time = time.time() - start_time
        
        # Should have taken at least 0.09 seconds (9 * 0.01)
        assert total_time >= 0.09
        assert total_time < 0.5  # But not too long


# Test configuration and fixtures
@pytest.fixture(scope="session")
def test_config():
    """Test configuration"""
    return {
        'test_video_id': 'test123abc',
        'test_channel_id': 'ch123abc',
        'test_query': 'bitcoin',
        'api_timeout': 30,
        'rate_limit': 0.5
    }


# Custom test markers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


# Test runner script
if __name__ == "__main__":
    """Run tests with coverage"""
    pytest.main([
        __file__,
        "--cov=bitchute",
        "--cov-report=html",
        "--cov-report=term-missing",
        "-v"
    ])