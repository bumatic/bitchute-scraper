"""
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
