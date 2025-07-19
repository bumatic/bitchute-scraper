"""
BitChute Scraper Custom Exceptions

Comprehensive exception hierarchy for BitChute API operations with detailed
error classification, context preservation, and diagnostic information.
Provides specific exception types for different failure modes to enable
precise error handling and debugging.

This module defines a complete exception framework that categorizes errors
by their root cause and provides detailed context for debugging and error
recovery. Each exception type includes specific attributes and methods
for comprehensive error analysis and user-friendly error reporting.

Exception Hierarchy:
    BitChuteAPIError (base)
    ├── TokenExtractionError - Authentication token extraction failures
    ├── RateLimitError - API rate limiting violations
    ├── ValidationError - Input validation failures
    ├── AuthenticationError - API authentication failures
    ├── NetworkError - Network and connectivity issues
    ├── DataProcessingError - Data parsing and processing failures
    └── ConfigurationError - Configuration and setup issues

All exceptions include detailed error messages, optional status codes,
and preserve original exception context for comprehensive error tracking.
"""


class BitChuteAPIError(Exception):
    """Base exception class for all BitChute API-related errors.

    Serves as the root exception for the BitChute scraper exception hierarchy,
    providing common functionality and attributes for all API-related errors.
    Includes support for HTTP status codes and detailed error context.

    This base class ensures consistent error handling patterns across the
    entire API client and provides a single exception type for catch-all
    error handling when specific error types are not needed.

    Attributes:
        message: Detailed error description
        status_code: HTTP status code if applicable (None for non-HTTP errors)

    Example:
        >>> try:
        ...     # API operation that may fail
        ...     result = api.get_trending_videos()
        ... except BitChuteAPIError as e:
        ...     print(f"API error: {e}")
        ...     if e.status_code:
        ...         print(f"HTTP status: {e.status_code}")
    """

    def __init__(self, message: str, status_code: int = None):
        """Initialize API error with message and optional status code.

        Args:
            message: Detailed description of the error condition
            status_code: HTTP status code if the error is HTTP-related

        Example:
            >>> error = BitChuteAPIError("Request failed", status_code=500)
            >>> print(str(error))  # "BitChute API Error (500): Request failed"
        """
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    def __str__(self):
        """Return formatted error message with optional status code.

        Returns:
            str: Formatted error message including status code if available
        """
        if self.status_code:
            return f"BitChute API Error ({self.status_code}): {self.message}"
        return f"BitChute API Error: {self.message}"


class TokenExtractionError(BitChuteAPIError):
    """Exception raised when authentication token extraction fails.

    Indicates failures in the token extraction process including web scraping
    failures, API endpoint unavailability, token validation failures, and
    browser automation issues. This error typically suggests authentication
    system problems that may require fallback strategies.

    Token extraction can fail due to:
    - BitChute website changes affecting scraping patterns
    - Network connectivity issues during token requests
    - Browser automation failures (WebDriver issues)
    - Invalid or malformed tokens from API responses
    - Rate limiting on token extraction endpoints

    Example:
        >>> try:
        ...     token = token_manager.get_token()
        ... except TokenExtractionError as e:
        ...     print(f"Token extraction failed: {e}")
        ...     # Implement fallback authentication strategy
        ...     token = fallback_token_method()
    """

    def __init__(self, message: str = "Failed to extract authentication token"):
        """Initialize token extraction error with descriptive message.

        Args:
            message: Specific description of the token extraction failure

        Example:
            >>> error = TokenExtractionError("WebDriver timeout during token extraction")
            >>> print(str(error))
        """
        super().__init__(message)


class RateLimitError(BitChuteAPIError):
    """Exception raised when API rate limits are exceeded.

    Indicates that the application has exceeded BitChute's API rate limits
    and requests are being throttled. This error includes the standard
    HTTP 429 status code and suggests that the application should implement
    exponential backoff or reduce request frequency.

    Rate limiting can occur due to:
    - Too many requests in a short time period
    - Concurrent requests exceeding allowed limits
    - Account-specific rate limit violations
    - Global API rate limit enforcement

    Example:
        >>> try:
        ...     videos = api.get_trending_videos(limit=1000)
        ... except RateLimitError as e:
        ...     print("Rate limit exceeded, implementing backoff...")
        ...     time.sleep(60)  # Wait before retrying
        ...     videos = api.get_trending_videos(limit=50)  # Reduce load
    """

    def __init__(self, message: str = "Rate limit exceeded"):
        """Initialize rate limit error with HTTP 429 status code.

        Args:
            message: Description of the rate limiting condition

        Example:
            >>> error = RateLimitError("Too many requests per minute")
            >>> print(error.status_code)  # 429
        """
        super().__init__(message, 429)


class ValidationError(BitChuteAPIError):
    """Exception raised for input validation failures.

    Indicates that user-provided input parameters failed validation checks
    before being sent to the API. Includes the specific field name that
    failed validation to enable precise error handling and user feedback.

    Validation errors can occur for:
    - Invalid parameter values (negative limits, invalid IDs)
    - Malformed input data (invalid date formats, bad URLs)
    - Security violations (suspicious query patterns, invalid characters)
    - Type mismatches (string where integer expected)
    - Range violations (values outside acceptable limits)

    Attributes:
        field: Name of the field that failed validation (if applicable)

    Example:
        >>> try:
        ...     api.get_trending_videos(limit=-5)
        ... except ValidationError as e:
        ...     print(f"Validation failed for field '{e.field}': {e}")
        ...     # Handle specific field error
        ...     if e.field == 'limit':
        ...         print("Please provide a positive limit value")
    """

    def __init__(self, message: str, field: str = None):
        """Initialize validation error with message and optional field name.

        Args:
            message: Description of the validation failure
            field: Name of the field that failed validation

        Example:
            >>> error = ValidationError("Value must be positive", field="limit")
            >>> print(f"Field: {error.field}")  # "limit"
        """
        self.field = field
        full_message = (
            f"Validation error for '{field}': {message}"
            if field
            else f"Validation error: {message}"
        )
        super().__init__(full_message)


class AuthenticationError(BitChuteAPIError):
    """Exception raised for API authentication failures.

    Indicates that API requests failed due to authentication issues such
    as invalid tokens, expired credentials, or insufficient permissions.
    Includes HTTP 401 status code and suggests token refresh or
    re-authentication may be required.

    Authentication errors can occur due to:
    - Expired authentication tokens
    - Invalid or malformed tokens
    - Revoked API access credentials
    - Insufficient permissions for requested operations
    - Account suspension or access restrictions

    Example:
        >>> try:
        ...     videos = api.get_member_picked_videos()
        ... except AuthenticationError as e:
        ...     print("Authentication failed, refreshing token...")
        ...     api.token_manager.invalidate_token()
        ...     new_token = api.token_manager.get_token()
        ...     videos = api.get_member_picked_videos()  # Retry with new token
    """

    def __init__(self, message: str = "Authentication failed"):
        """Initialize authentication error with HTTP 401 status code.

        Args:
            message: Description of the authentication failure

        Example:
            >>> error = AuthenticationError("Token expired")
            >>> print(error.status_code)  # 401
        """
        super().__init__(message, 401)


class NetworkError(BitChuteAPIError):
    """Exception raised for network-related failures.

    Indicates network connectivity issues, DNS resolution failures, timeout
    errors, or other network-level problems that prevent API communication.
    Provides context preservation for underlying network exceptions.

    Network errors can occur due to:
    - Internet connectivity loss
    - DNS resolution failures
    - Connection timeouts
    - SSL/TLS certificate issues
    - Proxy or firewall restrictions
    - Server unavailability

    Attributes:
        original_exception: Original network exception for detailed debugging

    Example:
        >>> try:
        ...     videos = api.get_trending_videos()
        ... except NetworkError as e:
        ...     print(f"Network error: {e}")
        ...     if e.original_exception:
        ...         print(f"Original error: {e.original_exception}")
        ...     # Implement retry with exponential backoff
        ...     retry_with_backoff()
    """

    def __init__(self, message: str = "Network error occurred"):
        """Initialize network error with context preservation.

        Args:
            message: Description of the network failure

        Example:
            >>> error = NetworkError("Connection timeout after 30 seconds")
            >>> error.original_exception = original_timeout_exception
        """
        super().__init__(message)
        # Store original exception for chaining
        self.original_exception = None


class DataProcessingError(BitChuteAPIError):
    """Exception raised during data parsing and processing operations.

    Indicates failures in processing API response data including JSON
    parsing errors, unexpected data formats, missing required fields,
    or data transformation failures. Suggests potential API changes
    or corrupted response data.

    Data processing errors can occur due to:
    - Invalid JSON in API responses
    - Unexpected response structure changes
    - Missing required fields in response data
    - Data type conversion failures
    - Malformed or corrupted response content
    - API version compatibility issues

    Example:
        >>> try:
        ...     videos = api.get_trending_videos()
        ... except DataProcessingError as e:
        ...     print(f"Data processing failed: {e}")
        ...     # Log raw response for debugging
        ...     logger.error(f"Raw response: {raw_response}")
        ...     # Implement fallback data processing
        ...     videos = process_data_with_fallback(raw_response)
    """

    def __init__(self, message: str = "Data processing error"):
        """Initialize data processing error with descriptive message.

        Args:
            message: Description of the data processing failure

        Example:
            >>> error = DataProcessingError("Missing 'videos' field in API response")
            >>> print(str(error))
        """
        super().__init__(message)


class ConfigurationError(BitChuteAPIError):
    """Exception raised for configuration and setup issues.

    Indicates problems with application configuration including invalid
    settings, missing dependencies, filesystem permissions, or environment
    setup issues that prevent proper operation.

    Configuration errors can occur due to:
    - Invalid configuration file values
    - Missing required directories or permissions
    - Incompatible dependency versions
    - Environment variable issues
    - Download directory creation failures
    - WebDriver setup problems

    Example:
        >>> try:
        ...     api = BitChuteAPI(download_base_dir="/invalid/path")
        ... except ConfigurationError as e:
        ...     print(f"Configuration error: {e}")
        ...     # Create valid download directory
        ...     os.makedirs("/valid/path", exist_ok=True)
        ...     api = BitChuteAPI(download_base_dir="/valid/path")
    """

    def __init__(self, message: str = "Configuration error"):
        """Initialize configuration error with descriptive message.

        Args:
            message: Description of the configuration issue

        Example:
            >>> error = ConfigurationError("Download directory is not writable")
            >>> print(str(error))
        """
        super().__init__(message)
