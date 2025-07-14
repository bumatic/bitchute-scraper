"""
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
