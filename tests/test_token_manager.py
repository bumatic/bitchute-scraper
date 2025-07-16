"""
Test token management functionality
"""

import pytest
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from bitchute.token_manager import TokenManager
from bitchute.exceptions import TokenExtractionError


@pytest.mark.selenium
class TestTokenManager:
    """Test TokenManager functionality"""
    
    @pytest.fixture
    def token_manager(self):
        """Create token manager without caching"""
        return TokenManager(cache_tokens=False, verbose=False)
    
    @pytest.fixture
    def cached_token_manager(self, tmp_path):
        """Create token manager with caching in temp directory"""
        manager = TokenManager(cache_tokens=True, verbose=False)
        manager.cache_file = tmp_path / "test_token.json"
        return manager
    
    def test_initialization(self):
        """Test TokenManager initialization"""
        # Without caching
        manager = TokenManager(cache_tokens=False, verbose=False)
        assert manager.cache_tokens == False
        assert manager.token is None
        assert manager.expires_at == 0
        
        # With caching
        manager = TokenManager(cache_tokens=True, verbose=True)
        assert manager.cache_tokens == True
        assert manager.verbose == True
    
    def test_token_validation(self, token_manager):
        """Test token format validation"""
        # Valid tokens (28 characters, alphanumeric + _ -)
        assert token_manager._is_valid_token("abcd1234efgh5678ijkl9012mnop")
        assert token_manager._is_valid_token("ABCD1234EFGH5678IJKL9012MNOP")
        assert token_manager._is_valid_token("1234567890123456789012345678")
        
        # Invalid tokens
        assert not token_manager._is_valid_token("")
        assert not token_manager._is_valid_token(None)
        assert not token_manager._is_valid_token("short")
        assert not token_manager._is_valid_token("too_long_token_1234567890123456789")
        assert not token_manager._is_valid_token("invalid@token#123456789012345")
        assert not token_manager._is_valid_token("has spaces 123456789012345")
        assert not token_manager._is_valid_token(123)  # Not a string
        assert not token_manager._is_valid_token("test_token-1234567890123456")
    
    def test_token_generation(self, token_manager):
        """Test token generation"""
        token1 = token_manager._generate_token()
        token2 = token_manager._generate_token()
        
        # Should generate valid tokens
        assert token_manager._is_valid_token(token1)
        assert token_manager._is_valid_token(token2)
        
        # Should be different
        assert token1 != token2
        
        # Should be 28 characters
        assert len(token1) == 28
        assert len(token2) == 28
    
    @patch('requests.post')
    def test_timer_api_extraction_success(self, mock_post, token_manager):
        """Test successful token extraction via timer API"""
        # Mock successful response with string token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = "abcd1234efgh5678ijkl9012mnop"
        mock_post.return_value = mock_response
        
        token = token_manager._extract_token_via_timer_api()
        
        assert token == "abcd1234efgh5678ijkl9012mnop"
        mock_post.assert_called_once()
        
        # Check request details
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://api.bitchute.com/api/timer/'
        assert call_args[1]['json'] == {}
        assert 'headers' in call_args[1]
    
    @patch('requests.post')
    def test_timer_api_extraction_dict_response(self, mock_post, token_manager):
        """Test timer API with dict response"""
        # Mock response with token in dict
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token": "abcd1234efgh5678ijkl9012mnop"
        }
        mock_post.return_value = mock_response
        
        token = token_manager._extract_token_via_timer_api()
        
        assert token == "abcd1234efgh5678ijkl9012mnop"
    
    @patch('requests.post')
    def test_timer_api_extraction_failure(self, mock_post, token_manager):
        """Test timer API extraction failure"""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        token = token_manager._extract_token_via_timer_api()
        
        assert token is None
    
    @patch('requests.post')
    def test_timer_api_extraction_network_error(self, mock_post, token_manager):
        """Test timer API with network error"""
        mock_post.side_effect = Exception("Network error")
        
        token = token_manager._extract_token_via_timer_api()
        
        assert token is None
    
    @patch('requests.post')
    def test_validate_generated_token(self, mock_post, token_manager):
        """Test generated token validation"""
        # Mock successful validation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        valid = token_manager._validate_generated_token("abcd1234efgh5678ijkl9012mnop")
        
        assert valid == True
        mock_post.assert_called_once()
        
        # Check validation request
        call_args = mock_post.call_args
        assert 'x-service-info' in call_args[1]['headers']
        assert call_args[1]['headers']['x-service-info'] == "abcd1234efgh5678ijkl9012mnop"
    
    @patch('requests.post')
    def test_validate_generated_token_failure(self, mock_post, token_manager):
        """Test generated token validation failure"""
        # Mock failed validation
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        valid = token_manager._validate_generated_token("bad_token_1234567890123456789")
        
        assert valid == False
    
    def test_token_caching(self, cached_token_manager):
        """Test token caching functionality"""
        # Set a token
        test_token = "cached_token_12345678901234567"
        cached_token_manager.token = test_token
        cached_token_manager.expires_at = time.time() + 3600
        
        # Save to cache
        cached_token_manager._save_token_cache()
        
        # Verify cache file exists
        assert cached_token_manager.cache_file.exists()
        
        # Load from cache
        new_manager = TokenManager(cache_tokens=True)
        new_manager.cache_file = cached_token_manager.cache_file
        new_manager._load_cached_token()
        
        assert new_manager.token == test_token
        assert new_manager.expires_at > time.time()
    
        def test_token_cache_expiration(self, tmp_path):
            """Test that expired cached tokens are not loaded"""
            # Create fresh manager without autouse fixture interference
            manager = TokenManager(cache_tokens=True, verbose=False)
            manager.cache_file = tmp_path / "test_token.json"
            
            # Set an expired token
            manager.token = "expired_token_123456789012345"
            manager.expires_at = time.time() - 3600  # Expired 1 hour ago
            
            # Save to cache
            manager._save_token_cache()
            
            # Create new manager and try to load
            new_manager = TokenManager(cache_tokens=True, verbose=False)
            new_manager.cache_file = manager.cache_file
            new_manager._load_cached_token()
            
            # Should not load expired token
            assert new_manager.token is None

    
    def test_token_cache_corruption(self, tmp_path):
        """Test handling of corrupted cache file"""
        manager = TokenManager(cache_tokens=True, verbose=False)
        manager.cache_file = tmp_path / "test_token.json"
        
        # Write invalid JSON to cache file
        manager.cache_file.write_text("invalid json{")
        
        print(manager.token)

        # Should not crash when loading
        manager._load_cached_token()

        print(manager.token)
        
        assert manager.token is None

    
    @patch('selenium.webdriver.Chrome')
    @patch('webdriver_manager.chrome.ChromeDriverManager')
    def test_webdriver_creation(self, mock_driver_manager, mock_chrome, token_manager):
        """Test webdriver creation"""
        # Mock driver manager
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"
        
        # Mock Chrome driver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        token_manager._create_webdriver()
        
        assert token_manager.webdriver is not None
        mock_chrome.assert_called_once()
        
        # Check options
        call_args = mock_chrome.call_args
        options = call_args[1]['options']
        assert options is not None
    
    @patch('selenium.webdriver.Chrome')
    def test_webdriver_cleanup(self, mock_chrome, token_manager):
        """Test webdriver cleanup"""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        token_manager.webdriver = mock_driver
        
        token_manager._close_webdriver()
        
        mock_driver.quit.assert_called_once()
        assert token_manager.webdriver is None
    
    @patch('selenium.webdriver.Chrome')
    def test_extract_token_from_page_success(self, mock_chrome, token_manager):
        """Test successful token extraction from page"""
        # Mock webdriver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Mock successful token extraction via JavaScript
        mock_driver.execute_script.return_value = "abcd1234efgh5678ijkl9012mnop"
        
        with patch.object(token_manager, '_create_webdriver'):
            with patch.object(token_manager, '_close_webdriver'):
                token_manager.webdriver = mock_driver
                token = token_manager._extract_token_from_page()
        
        assert token == "abcd1234efgh5678ijkl9012mnop"
        mock_driver.get.assert_called_with('https://www.bitchute.com/')
    
    @patch('selenium.webdriver.Chrome')
    def test_extract_token_from_page_timeout(self, mock_chrome, token_manager):
        """Test token extraction timeout"""
        from selenium.common.exceptions import TimeoutException
        
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        mock_driver.get.side_effect = TimeoutException("Page load timeout")
        
        with patch.object(token_manager, '_create_webdriver'):
            with patch.object(token_manager, '_close_webdriver'):
                token_manager.webdriver = mock_driver
                
                with pytest.raises(TokenExtractionError):
                    token_manager._extract_token_from_page()
    
    def test_extract_token_from_source(self, token_manager):
        """Test token extraction from page source"""
        # Test various token patterns
        test_cases = [
            ('"x-service-info": "abcd1234efgh5678ijkl9012mnop"', "abcd1234efgh5678ijkl9012mnop"),
            ("'x-service-info': 'ABCD1234EFGH5678IJKL9012MNOP'", "ABCD1234EFGH5678IJKL9012MNOP"),
            ('xServiceInfo: "1234567890123456789012345678"', "1234567890123456789012345678"),
        ]
        
        for source, expected in test_cases:
            token = token_manager._extract_token_from_source(source)
            assert token == expected
    
    def test_extract_token_from_source_no_match(self, token_manager):
        """Test token extraction with no match"""
        source = "This page has no token"
        token = token_manager._extract_token_from_source(source)
        assert token is None
    
    @patch.object(TokenManager, '_extract_token_via_timer_api')
    @patch.object(TokenManager, '_generate_token')
    @patch.object(TokenManager, '_validate_generated_token')
    def test_get_token_fallback_chain(self, mock_validate, mock_generate, mock_timer, token_manager):
        """Test token acquisition fallback chain"""
        # All methods fail
        mock_timer.return_value = None
        mock_generate.return_value = "generated_token_123456789012"
        mock_validate.return_value = False
        
        with patch.object(token_manager, '_extract_token_from_page', return_value=None):
            token = token_manager.get_token()
        
        # Should try all methods
        assert token is None
        mock_timer.assert_called_once()
        assert mock_generate.call_count >= 1
        assert mock_validate.call_count >= 1
    
    @patch.object(TokenManager, '_extract_token_via_timer_api')
    def test_get_token_success_first_try(self, mock_timer, token_manager):
        """Test successful token acquisition on first try"""
        mock_timer.return_value = "timer_token_123456789012345678"
        
        token = token_manager.get_token()
        
        assert token == "timer_token_123456789012345678"
        assert token_manager.token == token
        assert token_manager.expires_at > time.time()
    
    def test_get_token_uses_cached(self, token_manager):
        """Test that valid cached token is used"""
        # Set valid token
        token_manager.token = "cached_token_12345678901234567"
        token_manager.expires_at = time.time() + 3600
        
        token = token_manager.get_token()
        
        assert token == "cached_token_12345678901234567"
    
    def test_invalidate_token(self, cached_token_manager):
        """Test token invalidation"""
        # Set token
        cached_token_manager.token = "abcd1234efgh5678ijkl9012mnop"
        cached_token_manager.expires_at = time.time() + 3600
        cached_token_manager._save_token_cache()
        
        assert cached_token_manager.cache_file.exists()
        
        # Invalidate
        cached_token_manager.invalidate_token()
        
        assert cached_token_manager.token is None
        assert cached_token_manager.expires_at == 0
        assert not cached_token_manager.cache_file.exists()
    
    def test_has_valid_token(self, token_manager):
        """Test token validity check"""
        # No token
        assert not token_manager.has_valid_token()
        
        # Expired token
        token_manager.token = "expired_token_123456789012345"
        token_manager.expires_at = time.time() - 3600
        assert not token_manager.has_valid_token()
        
        # Valid token
        token_manager.token = "valid_token_123456789012345678"
        token_manager.expires_at = time.time() + 3600
        assert token_manager.has_valid_token()
    
    def test_get_token_info(self, token_manager):
        """Test token info retrieval"""
        info = token_manager.get_token_info()
        
        assert 'has_token' in info
        assert 'is_valid' in info
        assert 'expires_at' in info
        assert 'time_until_expiry' in info
        assert 'cache_enabled' in info
        
        assert info['has_token'] == False
        assert info['is_valid'] == False
    
    def test_context_manager(self, token_manager):
        """Test TokenManager as context manager"""
        with patch.object(token_manager, 'cleanup') as mock_cleanup:
            with token_manager as tm:
                assert tm is token_manager
            
            mock_cleanup.assert_called_once()
    
    def test_thread_safety(self, token_manager):
        """Test thread safety of token operations"""
        import threading
        
        results = []
        
        def get_token_thread():
            with patch.object(token_manager, '_extract_token_via_timer_api', 
                            return_value=f"thread_token_{threading.get_ident()}"):
                token = token_manager.get_token()
                results.append(token)
        
        threads = []
        for _ in range(5):
            t = threading.Thread(target=get_token_thread)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All threads should get a token
        assert len(results) == 5
        # But they should all get the same token (due to locking)
        assert len(set(results)) == 1