"""
Test custom exceptions
"""

import pytest

from bitchute.exceptions import (
    BitChuteAPIError,
    TokenExtractionError,
    RateLimitError,
    ValidationError,
    AuthenticationError,
    NetworkError,
    DataProcessingError,
    ConfigurationError
)


class TestBitChuteAPIError:
    """Test base BitChuteAPIError"""
    
    def test_basic_error(self):
        """Test basic error creation"""
        error = BitChuteAPIError("Test error message")
        
        assert str(error) == "BitChute API Error: Test error message"
        assert error.message == "Test error message"
        assert error.status_code is None
    
    def test_error_with_status_code(self):
        """Test error with HTTP status code"""
        error = BitChuteAPIError("Server error", 500)
        
        assert str(error) == "BitChute API Error (500): Server error"
        assert error.message == "Server error"
        assert error.status_code == 500
    
    def test_error_inheritance(self):
        """Test that custom error inherits from Exception"""
        error = BitChuteAPIError("Test")
        
        assert isinstance(error, Exception)
        assert isinstance(error, BitChuteAPIError)
    
    def test_error_raising(self):
        """Test raising the error"""
        with pytest.raises(BitChuteAPIError) as exc_info:
            raise BitChuteAPIError("Test error", 404)
        
        assert exc_info.value.message == "Test error"
        assert exc_info.value.status_code == 404


class TestTokenExtractionError:
    """Test TokenExtractionError"""
    
    def test_default_message(self):
        """Test error with default message"""
        error = TokenExtractionError()
        
        assert str(error) == "BitChute API Error: Failed to extract authentication token"
        assert isinstance(error, BitChuteAPIError)
    
    def test_custom_message(self):
        """Test error with custom message"""
        error = TokenExtractionError("Token expired")
        
        assert str(error) == "BitChute API Error: Token expired"
    
    def test_error_context(self):
        """Test error in context"""
        def extract_token():
            raise TokenExtractionError("Selenium failed")
        
        with pytest.raises(TokenExtractionError) as exc_info:
            extract_token()
        
        assert "Selenium failed" in str(exc_info.value)


class TestRateLimitError:
    """Test RateLimitError"""
    
    def test_default_message(self):
        """Test error with default message"""
        error = RateLimitError()
        
        assert str(error) == "BitChute API Error (429): Rate limit exceeded"
        assert error.status_code == 429
    
    def test_custom_message(self):
        """Test error with custom message"""
        error = RateLimitError("Too many requests, retry after 60s")
        
        assert "Too many requests" in str(error)
        assert error.status_code == 429
    
    def test_rate_limit_handling(self):
        """Test rate limit error in API context"""
        def make_api_call():
            # Simulate rate limit hit
            raise RateLimitError("API rate limit: 100 requests per hour")
        
        with pytest.raises(RateLimitError) as exc_info:
            make_api_call()
        
        assert exc_info.value.status_code == 429


class TestValidationError:
    """Test ValidationError"""
    
    def test_basic_validation_error(self):
        """Test basic validation error"""
        error = ValidationError("Invalid input")
        
        assert str(error) == "BitChute API Error: Validation error: Invalid input"
        assert error.field is None
    
    def test_validation_error_with_field(self):
        """Test validation error with field name"""
        error = ValidationError("Must be positive", "limit")
        
        assert str(error) == "BitChute API Error: Validation error for 'limit': Must be positive"
        assert error.field == "limit"
    
    def test_validation_error_raising(self):
        """Test raising validation errors"""
        def validate_limit(value):
            if value <= 0:
                raise ValidationError("Limit must be positive", "limit")
        
        with pytest.raises(ValidationError) as exc_info:
            validate_limit(-1)
        
        assert exc_info.value.field == "limit"
        assert "must be positive" in str(exc_info.value)
    
    def test_multiple_validation_errors(self):
        """Test handling multiple validation errors"""
        errors = []
        
        try:
            raise ValidationError("Invalid format", "video_id")
        except ValidationError as e:
            errors.append(e)
        
        try:
            raise ValidationError("Too long", "query")
        except ValidationError as e:
            errors.append(e)
        
        assert len(errors) == 2
        assert errors[0].field == "video_id"
        assert errors[1].field == "query"


class TestAuthenticationError:
    """Test AuthenticationError"""
    
    def test_default_message(self):
        """Test error with default message"""
        error = AuthenticationError()
        
        assert str(error) == "BitChute API Error (401): Authentication failed"
        assert error.status_code == 401
    
    def test_custom_auth_message(self):
        """Test error with custom message"""
        error = AuthenticationError("Invalid token")
        
        assert "Invalid token" in str(error)
        assert error.status_code == 401
    
    def test_auth_error_context(self):
        """Test authentication error in API context"""
        def authenticate():
            raise AuthenticationError("Token has expired, please refresh")
        
        with pytest.raises(AuthenticationError) as exc_info:
            authenticate()
        
        assert "expired" in str(exc_info.value)


class TestNetworkError:
    """Test NetworkError"""
    
    def test_default_message(self):
        """Test error with default message"""
        error = NetworkError()
        
        assert str(error) == "BitChute API Error: Network error occurred"
    
    def test_network_error_with_details(self):
        """Test error with network details"""
        error = NetworkError("Connection timeout after 30s")
        
        assert "Connection timeout" in str(error)

    def test_network_error_chaining(self):
        """Test error chaining with original exception"""
        import requests
        
        # Test that NetworkError can be raised from another exception
        with pytest.raises(NetworkError):
            try:
                raise requests.ConnectionError("Failed to establish connection")
            except requests.ConnectionError as e:
                raise NetworkError("API request failed") from e

class TestDataProcessingError:
    """Test DataProcessingError"""
    
    def test_default_message(self):
        """Test error with default message"""
        error = DataProcessingError()
        
        assert str(error) == "BitChute API Error: Data processing error"
    
    def test_processing_error_with_details(self):
        """Test error with processing details"""
        error = DataProcessingError("Failed to parse video data: invalid JSON")
        
        assert "Failed to parse video data" in str(error)
        assert "invalid JSON" in str(error)
    
    def test_processing_error_context(self):
        """Test processing error in data pipeline"""
        def process_data(data):
            if not isinstance(data, dict):
                raise DataProcessingError(f"Expected dict, got {type(data).__name__}")
        
        with pytest.raises(DataProcessingError) as exc_info:
            process_data("invalid")
        
        assert "Expected dict, got str" in str(exc_info.value)


class TestConfigurationError:
    """Test ConfigurationError"""
    
    def test_default_message(self):
        """Test error with default message"""
        error = ConfigurationError()
        
        assert str(error) == "BitChute API Error: Configuration error"
    
    def test_config_error_with_details(self):
        """Test error with configuration details"""
        error = ConfigurationError("Missing required environment variable: API_KEY")
        
        assert "Missing required environment variable" in str(error)
        assert "API_KEY" in str(error)
    
    def test_config_validation(self):
        """Test configuration validation errors"""
        def validate_config(config):
            if 'timeout' in config and config['timeout'] <= 0:
                raise ConfigurationError("Timeout must be positive")
        
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config({'timeout': -1})
        
        assert "Timeout must be positive" in str(exc_info.value)


class TestExceptionHierarchy:
    """Test exception hierarchy and relationships"""
    
    def test_all_inherit_from_base(self):
        """Test that all custom exceptions inherit from BitChuteAPIError"""
        exceptions = [
            TokenExtractionError(),
            RateLimitError(),
            ValidationError("test"),
            AuthenticationError(),
            NetworkError(),
            DataProcessingError(),
            ConfigurationError()
        ]
        
        for exc in exceptions:
            assert isinstance(exc, BitChuteAPIError)
            assert isinstance(exc, Exception)
    
    def test_exception_catching(self):
        """Test catching exceptions at different levels"""
        # Catch specific exception
        try:
            raise RateLimitError()
        except RateLimitError:
            pass
        
        # Catch base exception
        try:
            raise ValidationError("test")
        except BitChuteAPIError:
            pass
        
        # Catch as generic exception
        try:
            raise NetworkError()
        except Exception:
            pass
    
    def test_exception_types(self):
        """Test exception type checking"""
        errors = {
            'token': TokenExtractionError(),
            'rate': RateLimitError(),
            'validation': ValidationError("test"),
            'auth': AuthenticationError(),
            'network': NetworkError(),
            'processing': DataProcessingError(),
            'config': ConfigurationError()
        }
        
        # Check types
        assert isinstance(errors['rate'], RateLimitError)
        assert not isinstance(errors['rate'], ValidationError)
        
        # Check all are BitChuteAPIError
        assert all(isinstance(e, BitChuteAPIError) for e in errors.values())


class TestExceptionUsagePatterns:
    """Test common exception usage patterns"""
    
    def test_api_error_handling_pattern(self):
        """Test typical API error handling pattern"""
        def api_call():
            # Simulate different error scenarios
            import random
            error_type = random.choice(['rate', 'auth', 'network'])
            
            if error_type == 'rate':
                raise RateLimitError()
            elif error_type == 'auth':
                raise AuthenticationError("Invalid token")
            else:
                raise NetworkError("Connection failed")
        
        # Handle specific errors differently
        try:
            api_call()
        except RateLimitError:
            # Would implement backoff strategy
            pass
        except AuthenticationError:
            # Would refresh token
            pass
        except NetworkError:
            # Would retry with different endpoint
            pass
        except BitChuteAPIError:
            # Catch-all for other API errors
            pass
    
    def test_validation_chain(self):
        """Test validation error chain"""
        def validate_request(data):
            errors = []
            
            if 'limit' not in data:
                errors.append(ValidationError("Missing required field", "limit"))
            elif data['limit'] <= 0:
                errors.append(ValidationError("Must be positive", "limit"))
            
            if 'query' in data and len(data['query']) > 100:
                errors.append(ValidationError("Too long", "query"))
            
            if errors:
                # In practice, might combine errors
                raise errors[0]
        
        # Test missing field
        with pytest.raises(ValidationError) as exc:
            validate_request({})
        assert exc.value.field == "limit"
        
        # Test invalid value
        with pytest.raises(ValidationError) as exc:
            validate_request({'limit': -1})
        assert "positive" in str(exc.value)
    
    def test_error_context_preservation(self):
        """Test preserving error context"""
        def low_level_operation():
            raise ValueError("Invalid data format")
        
        def high_level_operation():
            try:
                low_level_operation()
            except ValueError as e:
                raise DataProcessingError(f"Operation failed: {str(e)}") from e
        
        with pytest.raises(DataProcessingError) as exc_info:
            high_level_operation()
        
        assert "Operation failed" in str(exc_info.value)
        assert "Invalid data format" in str(exc_info.value)
        assert exc_info.value.__cause__ is not None