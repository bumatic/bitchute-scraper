"""
BitChute Scraper Exceptions
"""

class BitChuteAPIError(Exception):
    """Base exception for BitChute API errors"""
    
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)
    
    def __str__(self):
        if self.status_code:
            return f"BitChute API Error ({self.status_code}): {self.message}"
        return f"BitChute API Error: {self.message}"


class TokenExtractionError(BitChuteAPIError):
    """Exception raised when token extraction fails"""
    
    def __init__(self, message: str = "Failed to extract authentication token"):
        super().__init__(message)


class RateLimitError(BitChuteAPIError):
    """Exception raised when rate limit is exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, 429)


class ValidationError(BitChuteAPIError):
    """Exception raised for validation errors"""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        full_message = f"Validation error for '{field}': {message}" if field else f"Validation error: {message}"
        super().__init__(full_message)


class AuthenticationError(BitChuteAPIError):
    """Exception raised for authentication errors"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, 401)


class NetworkError(BitChuteAPIError):
    """Exception raised for network-related errors"""
    
    def __init__(self, message: str = "Network error occurred"):
        super().__init__(message)


class DataProcessingError(BitChuteAPIError):
    """Exception raised during data processing"""
    
    def __init__(self, message: str = "Data processing error"):
        super().__init__(message)


class ConfigurationError(BitChuteAPIError):
    """Exception raised for configuration errors"""
    
    def __init__(self, message: str = "Configuration error"):
        super().__init__(message)