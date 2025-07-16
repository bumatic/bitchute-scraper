"""
Test core BitChute API functionality
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, call
import time

from bitchute.core import BitChuteAPI, SensitivityLevel, SortOrder, VideoSelection
from bitchute.exceptions import BitChuteAPIError, RateLimitError, ValidationError
from bitchute.models import Video, Channel

from .fixtures import (
    mock_video_data, mock_channel_data, mock_api_client,
    create_mock_video_data, create_mock_api_response
)
from .helpers import (
    assert_valid_dataframe, assert_valid_video, assert_api_call_made,
    time_limit
)


class TestBitChuteAPIInitialization:
    """Test API client initialization"""
    
    def test_default_initialization(self):
        """Test API client with default parameters"""
        api = BitChuteAPI()
        
        assert api.verbose == False
        assert api.timeout == 30
        assert api.max_retries == 3
        assert api.base_url == "https://api.bitchute.com/api"
        assert hasattr(api, 'session')
        assert hasattr(api, 'token_manager')
        assert hasattr(api, 'rate_limiter')
        assert hasattr(api, 'validator')
    
    def test_custom_initialization(self):
        """Test API client with custom parameters"""
        api = BitChuteAPI(
            verbose=True,
            cache_tokens=False,
            rate_limit=1.0,
            timeout=60,
            max_retries=5
        )
        
        assert api.verbose == True
        assert api.timeout == 60
        assert api.max_retries == 5
        assert api.rate_limiter.rate_limit == 1.0
    
    def test_session_configuration(self):
        """Test session headers and configuration"""
        api = BitChuteAPI()
        headers = api.session.headers
        
        # Check required headers
        assert 'accept' in headers
        assert 'content-type' in headers
        assert headers['content-type'] == 'application/json'
        assert 'origin' in headers
        assert headers['origin'] == 'https://www.bitchute.com'
        assert 'referer' in headers
        assert 'user-agent' in headers
    
    def test_context_manager(self):
        """Test API client as context manager"""
        with BitChuteAPI() as api:
            assert isinstance(api, BitChuteAPI)
            assert hasattr(api, 'session')
        
        # After exiting context, resources should be cleaned up
        assert api.session is not None  # Session still exists but should be closed


class TestAPIRequests:
    """Test API request handling"""
    
    @pytest.fixture
    def api(self, mock_token_manager):
        """Create API client with mocked token manager"""
        api = BitChuteAPI(verbose=False)
        api.token_manager = mock_token_manager
        return api
    
    @patch('bitchute.core.requests.Session.post')
    def test_successful_request(self, mock_post, api):
        """Test successful API request"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": "test"}
        mock_post.return_value = mock_response
        
        result = api._make_request("beta/videos", {"limit": 10})
        
        assert result == {"success": True, "data": "test"}
        mock_post.assert_called_once()
        
        # Check request details
        call_args = mock_post.call_args
        assert call_args[0][0].endswith("beta/videos")
        assert call_args[1]['json'] == {"limit": 10}
        assert call_args[1]['timeout'] == 30
    
    @patch('bitchute.core.requests.Session.post')
    def test_rate_limit_error(self, mock_post, api):
        """Test rate limit error handling"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        
        with pytest.raises(RateLimitError):
            api._make_request("beta/videos", {"limit": 10})
        
        assert api.stats['errors'] == 3
    
    @patch('bitchute.core.requests.Session.post')
    def test_api_error_handling(self, mock_post, api):
        """Test general API error handling"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        with pytest.raises(BitChuteAPIError) as exc_info:
            api._make_request("beta/videos", {"limit": 10})
        
        assert "500" in str(exc_info.value)
        assert api.stats['errors'] == 3
    
    @patch('bitchute.core.requests.Session.post')
    def test_token_refresh_on_401(self, mock_post, api):
        """Test token refresh on authentication error"""
        # First request fails with 401, second succeeds
        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"success": True}
        
        mock_post.side_effect = [mock_response_401, mock_response_200]
        
        result = api._make_request("beta/videos", {"limit": 10})
        
        assert result == {"success": True}
        assert mock_post.call_count == 2
        api.token_manager.invalidate_token.assert_called_once()
        assert api.token_manager.get_token.call_count == 2
    
    def test_request_without_token(self, api):
        """Test request without requiring token"""
        with patch.object(api.session, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"hashtags": []}
            mock_post.return_value = mock_response
            
            api._make_request("beta9/hashtag/trending/", {"dummy": 1}, require_token=False)
            
            # Token manager should not be called
            api.token_manager.get_token.assert_not_called()


class TestTrendingVideos:
    """Test trending videos functionality"""
    
    @pytest.fixture
    def api(self):
        api = BitChuteAPI(verbose=False)
        return api
    
    def test_trending_videos_validation(self, api):
        """Test input validation for trending videos"""
        # Invalid timeframe
        with pytest.raises(ValidationError):
            api.get_trending_videos("invalid")
        
        # Invalid limit
        with pytest.raises(ValidationError):
            api.get_trending_videos("day", limit=0)
        
        # Invalid per_page
        with pytest.raises(ValidationError):
            api.get_trending_videos("day", per_page=150)
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_get_trending_videos_success(self, mock_request, api, mock_video_data):
        """Test successful trending videos retrieval"""
        mock_request.return_value = {"videos": [mock_video_data]}
        
        result = api.get_trending_videos("day", limit=1)
        
        assert_valid_dataframe(result, ['id', 'title', 'view_count'], min_rows=1)
        assert result.iloc[0]['id'] == "test123abc"
        assert result.iloc[0]['title'] == "Test Video Title"
        assert result.iloc[0]['view_count'] == 1500
        
        # Check API call
        mock_request.assert_called_with(
            "beta/videos",
            {
                "selection": "trending-day",
                "offset": 0,
                "limit": 1,
                "advertisable": True
            }
        )
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_get_trending_videos_pagination(self, mock_request, api):
        """Test pagination for trending videos"""
        # Mock paginated responses
        page1 = {"videos": [create_mock_video_data(f"video{i}") for i in range(50)]}
        page2 = {"videos": [create_mock_video_data(f"video{i}") for i in range(50, 75)]}
        page3 = {"videos": []}  # Empty page indicates end
        
        mock_request.side_effect = [page1, page2, page3]
        
        result = api.get_trending_videos("week", limit=75, per_page=50)
        
        assert len(result) == 75
        assert mock_request.call_count == 2 #3
        
        # Check pagination offsets
        calls = mock_request.call_args_list
        assert calls[0][0][1]['offset'] == 0
        assert calls[1][0][1]['offset'] == 50
    
    @patch.object(BitChuteAPI, '_make_request')
    @patch.object(BitChuteAPI, '_enrich_video_details')
    def test_get_trending_videos_with_details(self, mock_enrich, mock_request, api, mock_video_data):
        """Test trending videos with detail enrichment"""
        mock_request.return_value = {"videos": [mock_video_data]}
        
        result = api.get_trending_videos("month", limit=1, include_details=True)
        
        assert len(result) == 1
        mock_enrich.assert_called_once()
    
    def test_trending_timeframe_mapping(self, api):
        """Test timeframe to selection mapping"""
        with patch.object(api, '_make_request') as mock_request:
            mock_request.return_value = {"videos": []}
            
            # Test day
            api.get_trending_videos("day", limit=1)
            assert mock_request.call_args[0][1]['selection'] == "trending-day"
            
            # Test week
            api.get_trending_videos("week", limit=1)
            assert mock_request.call_args[0][1]['selection'] == "trending-week"
            
            # Test month
            api.get_trending_videos("month", limit=1)
            assert mock_request.call_args[0][1]['selection'] == "trending-month"


class TestVideoSearch:
    """Test video search functionality"""
    
    @pytest.fixture
    def api(self):
        return BitChuteAPI(verbose=False)
    
    def test_search_validation(self, api):
        """Test search input validation"""
        # Empty query
        with pytest.raises(ValidationError):
            api.search_videos("")
        
        # Query too long
        with pytest.raises(ValidationError):
            api.search_videos("a" * 101)
        
        # Invalid sensitivity
        with pytest.raises(ValidationError):
            api.search_videos("test", sensitivity="invalid")
        
        # Invalid sort order
        with pytest.raises(ValidationError):
            api.search_videos("test", sort="invalid")
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_search_videos_success(self, mock_request, api, mock_video_data):
        """Test successful video search"""
        mock_request.return_value = {"videos": [mock_video_data]}
        
        result = api.search_videos("bitcoin", limit=1)
        
        assert_valid_dataframe(result, ['id', 'title'], min_rows=1)
        
        mock_request.assert_called_with(
            "beta/search/videos",
            {
                "offset": 0,
                "limit": 1,
                "query": "bitcoin",
                "sensitivity_id": "normal",
                "sort": "new"
            }
        )
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_search_with_options(self, mock_request, api):
        """Test search with various options"""
        mock_request.return_value = {"videos": []}
        
        api.search_videos(
            "test query",
            sensitivity=SensitivityLevel.NSFW,
            sort=SortOrder.VIEWS,
            limit=50
        )
        
        call_payload = mock_request.call_args[0][1]
        assert call_payload['sensitivity_id'] == "nsfw"
        assert call_payload['sort'] == "views"
        assert call_payload['limit'] == 50
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_search_pagination(self, mock_request, api):
        """Test search pagination"""
        # Create 150 mock videos
        all_videos = [create_mock_video_data(f"video{i}") for i in range(150)]
        
        # Mock paginated responses
        mock_request.side_effect = [
            {"videos": all_videos[0:50]},
            {"videos": all_videos[50:100]},
            {"videos": all_videos[100:150]},
            {"videos": []}  # Empty page
        ]
        
        result = api.search_videos("test", limit=150, per_page=50)
        
        assert len(result) == 150
        assert mock_request.call_count == 3


class TestVideoDetails:
    """Test video details functionality"""
    
    @pytest.fixture
    def api(self):
        return BitChuteAPI(verbose=False)
    
    def test_video_id_validation(self, api):
        """Test video ID validation"""
        with pytest.raises(ValidationError):
            api.get_video_details("")
        
        with pytest.raises(ValidationError):
            api.get_video_details("abc")  # Too short
        
        with pytest.raises(ValidationError):
            api.get_video_details("invalid@id#")  # Invalid characters
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_get_video_details_basic(self, mock_request, api):
        """Test basic video details retrieval"""
        video_data = {
            "video_id": "test123abc",
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
        
        mock_request.return_value = video_data
        
        result = api.get_video_details("test123abc", include_counts=False)
        
        assert_valid_video(result)
        assert result.id == "test123abc"
        assert result.title == "Test Video"
        assert result.view_count == 1000
        
        mock_request.assert_called_once_with(
            "beta9/video",
            {"video_id": "test123abc"},
            require_token=False
        )
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_get_video_details_with_counts(self, mock_request, api):
        """Test video details with engagement counts"""
        video_data = {
            "video_id": "test123abc",
            "video_name": "Test Video",
            "view_count": 1000
        }
        
        counts_data = {
            "like_count": 100,
            "dislike_count": 10,
            "view_count": 1100  # Updated count
        }
        
        mock_request.side_effect = [video_data, counts_data]
        
        result = api.get_video_details("test123abc", include_counts=True)
        
        assert result.like_count == 100
        assert result.dislike_count == 10
        assert result.view_count == 1100  # Should use updated count
        
        assert mock_request.call_count == 2
        assert mock_request.call_args_list[1][0][0] == "beta/video/counts"
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_get_video_details_with_media(self, mock_request, api):
        """Test video details with media URL"""
        video_data = {"video_id": "test123abc", "video_name": "Test"}
        counts_data = {"like_count": 50, "dislike_count": 5}
        media_data = {
            "media_url": "https://example.com/video.mp4",
            "media_type": "video/mp4"
        }
        
        mock_request.side_effect = [video_data, counts_data, media_data]
        
        result = api.get_video_details(
            "test123abc",
            include_counts=True,
            include_media=True
        )
        
        assert result.media_url == "https://example.com/video.mp4"
        assert result.media_type == "video/mp4"
        assert mock_request.call_count == 3


class TestChannelOperations:
    """Test channel-related operations"""
    
    @pytest.fixture
    def api(self):
        return BitChuteAPI(verbose=False)
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_search_channels(self, mock_request, api, mock_channel_data):
        """Test channel search"""
        mock_request.return_value = {"channels": [mock_channel_data]}
        
        result = api.search_channels("test", limit=1)
        
        assert_valid_dataframe(result, ['id', 'name'], min_rows=1)
        assert result.iloc[0]['id'] == "ch123abc"
        assert result.iloc[0]['name'] == "Test Channel"
        
        mock_request.assert_called_with(
            "beta/search/channels",
            {
                "offset": 0,
                "limit": 1,
                "query": "test",
                "sensitivity_id": "normal"
            }
        )
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_get_channel_details(self, mock_request, api, mock_channel_data):
        """Test channel details retrieval"""
        mock_request.return_value = mock_channel_data
        
        result = api.get_channel_details("ch123abc")
        
        assert isinstance(result, Channel)
        assert result.id == "ch123abc"
        assert result.name == "Test Channel"
        assert result.video_count == 150
        
        mock_request.assert_called_with(
            "beta/channel",
            {"channel_id": "ch123abc"}
        )
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_get_channel_videos(self, mock_request, api):
        """Test getting videos from a channel"""
        videos = [create_mock_video_data(f"video{i}") for i in range(5)]
        mock_request.return_value = {"videos": videos}
        
        result = api.get_channel_videos("ch123abc", limit=5)
        
        assert len(result) == 5
        mock_request.assert_called_with(
            "beta/channel/videos",
            {
                "channel_id": "ch123abc",
                "offset": 0,
                "limit": 5,
                "order_by": "latest"
            }
        )


class TestHashtagOperations:
    """Test hashtag-related operations"""
    
    @pytest.fixture
    def api(self):
        return BitChuteAPI(verbose=False)
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_get_trending_hashtags(self, mock_request, api):
        """Test trending hashtags retrieval"""
        hashtag_data = [
            {"hashtag_id": "bitcoin", "hashtag_count": 1000},
            {"hashtag_id": "crypto", "hashtag_count": 800},
            {"hashtag_id": "news", "hashtag_count": 600}
        ]
        
        mock_request.return_value = {"hashtags": hashtag_data}
        
        result = api.get_trending_hashtags(limit=3)
        
        assert_valid_dataframe(result, ['name', 'rank'], min_rows=3)
        assert result.iloc[0]['name'] == "bitcoin"
        assert result.iloc[0]['rank'] == 1
        assert result.iloc[1]['rank'] == 2
        
        mock_request.assert_called_with(
            "beta9/hashtag/trending/",
            {"offset": 0, "limit": 3},
            require_token=False
        )


class TestStatistics:
    """Test API statistics"""
    
    def test_api_stats_tracking(self):
        """Test that API tracks statistics correctly"""
        api = BitChuteAPI(verbose=False)
        
        initial_stats = api.get_api_stats()
        assert initial_stats['requests_made'] == 0
        assert initial_stats['errors'] == 0
        
        # Make a failed request
        with patch.object(api.session, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response
            
            try:
                api._make_request("test", {})
            except BitChuteAPIError:
                pass
        
        stats = api.get_api_stats()
        assert stats['requests_made'] == 1
        assert stats['errors'] == 1
        assert stats['error_rate'] == 1.0