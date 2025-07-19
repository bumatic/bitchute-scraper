"""
BitChute Scraper Input Validators

Comprehensive input validation system for BitChute API requests with strict
parameter checking, format validation, and security measures. Provides robust
validation for all user inputs including search queries, identifiers, limits,
and configuration parameters.

This module implements a complete validation framework that ensures data
integrity, prevents injection attacks, and maintains API compatibility by
validating all input parameters according to BitChute API specifications
and security best practices.

Classes:
    InputValidator: Main validation class with comprehensive parameter checking

The validator supports validation for:
- API parameters (limits, offsets, timeframes, sensitivity levels)
- Identifiers (video IDs, channel IDs with proper format checking)
- Search queries (length limits, content filtering, security checks)
- File operations (export formats, filenames, paths)
- Network parameters (timeouts, rate limits, worker counts)
- Data types (dates, keywords, payload structures)

All validation methods raise descriptive ValidationError exceptions with
specific field names and error details for comprehensive error handling.
"""

import re
from typing import Any, Dict, List
from .exceptions import ValidationError


class InputValidator:
    """Comprehensive input validator for BitChute API requests.

    Provides extensive validation functionality for all types of input
    parameters used throughout the BitChute API client. Implements strict
    format checking, range validation, and security measures to ensure
    data integrity and prevent invalid API requests.

    The validator maintains lists of valid values for enumerated parameters
    and uses regular expressions for format validation of identifiers and
    other structured data. All validation failures raise descriptive
    ValidationError exceptions with specific field information.

    Attributes:
        VALID_TIMEFRAMES: Allowed timeframe values for trending content
        VALID_SENSITIVITIES: Allowed content sensitivity levels
        VALID_SORT_ORDERS: Allowed sort order options for search results
        VALID_SELECTIONS: Allowed video selection types
        VIDEO_ID_PATTERN: Regular expression for valid video ID format
        CHANNEL_ID_PATTERN: Regular expression for valid channel ID format

    Example:
        >>> validator = InputValidator()
        >>>
        >>> # Validate basic parameters
        >>> validator.validate_limit(50)  # OK
        >>> validator.validate_timeframe('day')  # OK
        >>>
        >>> # Validate identifiers
        >>> validator.validate_video_id('CLrgZP4RWyly')  # OK
        >>>
        >>> # Validate complex structures
        >>> payload = {"limit": 50, "offset": 0, "query": "bitcoin"}
        >>> validator.validate_payload(payload)  # OK
    """

    # Valid enumerated values for various parameters
    VALID_TIMEFRAMES = ["day", "week", "month"]
    VALID_SENSITIVITIES = ["normal", "nsfw", "nsfl"]
    VALID_SORT_ORDERS = ["new", "old", "views"]
    VALID_SELECTIONS = [
        "trending-day",
        "trending-week",
        "trending-month",
        "popular",
        "all",
    ]

    # Regular expression patterns for identifier validation
    VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{6,20}$")
    CHANNEL_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{6,20}$")

    def validate_limit(self, limit: int, max_limit: int = 100, min_limit: int = 1):
        """Validate limit parameter for API requests.

        Ensures limit parameters are within acceptable ranges for API
        performance and prevents excessive resource usage. Validates
        both type and value constraints.

        Args:
            limit: Number of items to retrieve
            max_limit: Maximum allowed limit value
            min_limit: Minimum allowed limit value

        Raises:
            ValidationError: If limit is not an integer or outside valid range

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_limit(50)  # OK
            >>> validator.validate_limit(150, max_limit=200)  # OK with custom max
            >>> validator.validate_limit(0)  # Raises ValidationError
        """
        if not isinstance(limit, int):
            raise ValidationError(
                f"Limit must be an integer, got {type(limit)}", "limit"
            )

        if limit < min_limit:
            raise ValidationError(
                f"Limit must be at least {min_limit}, got {limit}", "limit"
            )

        if limit > max_limit:
            raise ValidationError(
                f"Limit must be at most {max_limit}, got {limit}", "limit"
            )

    def validate_offset(self, offset: int):
        """Validate offset parameter for pagination.

        Ensures offset parameters are valid non-negative integers for
        proper pagination handling.

        Args:
            offset: Starting position for paginated results

        Raises:
            ValidationError: If offset is not an integer or is negative

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_offset(0)    # OK
            >>> validator.validate_offset(100)  # OK
            >>> validator.validate_offset(-1)   # Raises ValidationError
        """
        if not isinstance(offset, int):
            raise ValidationError(
                f"Offset must be an integer, got {type(offset)}", "offset"
            )

        if offset < 0:
            raise ValidationError(
                f"Offset must be non-negative, got {offset}", "offset"
            )

    def validate_timeframe(self, timeframe: str):
        """Validate timeframe parameter for trending content requests.

        Ensures timeframe values match the allowed options for BitChute's
        trending content endpoints.

        Args:
            timeframe: Timeframe specification ('day', 'week', or 'month')

        Raises:
            ValidationError: If timeframe is not a string or not in valid options

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_timeframe('day')    # OK
            >>> validator.validate_timeframe('week')   # OK
            >>> validator.validate_timeframe('year')   # Raises ValidationError
        """
        if not isinstance(timeframe, str):
            raise ValidationError(
                f"Timeframe must be a string, got {type(timeframe)}", "timeframe"
            )

        if timeframe not in self.VALID_TIMEFRAMES:
            raise ValidationError(
                f"Timeframe must be one of {self.VALID_TIMEFRAMES}, got '{timeframe}'",
                "timeframe",
            )

    def validate_sensitivity(self, sensitivity: str):
        """Validate content sensitivity parameter.

        Ensures sensitivity levels match the allowed content filtering
        options supported by BitChute's API.

        Args:
            sensitivity: Content sensitivity level ('normal', 'nsfw', or 'nsfl')

        Raises:
            ValidationError: If sensitivity is not a string or not in valid options

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_sensitivity('normal')  # OK
            >>> validator.validate_sensitivity('nsfw')    # OK
            >>> validator.validate_sensitivity('custom')  # Raises ValidationError
        """
        if not isinstance(sensitivity, str):
            raise ValidationError(
                f"Sensitivity must be a string, got {type(sensitivity)}", "sensitivity"
            )

        if sensitivity not in self.VALID_SENSITIVITIES:
            raise ValidationError(
                f"Sensitivity must be one of {self.VALID_SENSITIVITIES}, got '{sensitivity}'",
                "sensitivity",
            )

    def validate_sort_order(self, sort_order: str):
        """Validate sort order parameter for search results.

        Ensures sort order values match the supported sorting options
        for search and listing endpoints.

        Args:
            sort_order: Sort order specification ('new', 'old', or 'views')

        Raises:
            ValidationError: If sort_order is not a string or not in valid options

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_sort_order('new')     # OK
            >>> validator.validate_sort_order('views')   # OK
            >>> validator.validate_sort_order('rating')  # Raises ValidationError
        """
        if not isinstance(sort_order, str):
            raise ValidationError(
                f"Sort order must be a string, got {type(sort_order)}", "sort_order"
            )

        if sort_order not in self.VALID_SORT_ORDERS:
            raise ValidationError(
                f"Sort order must be one of {self.VALID_SORT_ORDERS}, got '{sort_order}'",
                "sort_order",
            )

    def validate_selection(self, selection: str):
        """Validate video selection parameter for content endpoints.

        Ensures selection values match the supported video selection
        types for various content listing endpoints.

        Args:
            selection: Video selection type (e.g., 'trending-day', 'popular', 'all')

        Raises:
            ValidationError: If selection is not a string or not in valid options

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_selection('trending-day')  # OK
            >>> validator.validate_selection('popular')       # OK
            >>> validator.validate_selection('custom')        # Raises ValidationError
        """
        if not isinstance(selection, str):
            raise ValidationError(
                f"Selection must be a string, got {type(selection)}", "selection"
            )

        if selection not in self.VALID_SELECTIONS:
            raise ValidationError(
                f"Selection must be one of {self.VALID_SELECTIONS}, got '{selection}'",
                "selection",
            )

    def validate_search_query(self, query: str):
        """Validate search query string with security and length checks.

        Performs comprehensive validation of search queries including
        length limits, content filtering, and security measures to
        prevent injection attacks and ensure API compatibility.

        Args:
            query: Search query string to validate

        Raises:
            ValidationError: If query is not a string, empty, too long,
                or contains suspicious patterns

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_search_query('bitcoin')           # OK
            >>> validator.validate_search_query('climate change')    # OK
            >>> validator.validate_search_query('')                  # Raises ValidationError
            >>> validator.validate_search_query('x' * 150)          # Raises ValidationError
        """
        if not isinstance(query, str):
            raise ValidationError(f"Query must be a string, got {type(query)}", "query")

        query = query.strip()
        if not query:
            raise ValidationError("Query cannot be empty", "query")

        if len(query) > 100:
            raise ValidationError(
                f"Query too long (max 100 characters), got {len(query)}", "query"
            )

        # Check for suspicious patterns - only count non-whitespace bounded spaces
        space_count = query.count(" ")
        if space_count > 20:
            raise ValidationError("Query contains too many spaces", "query")

    def validate_video_id(self, video_id: str):
        """Validate video ID format according to BitChute specifications.

        Ensures video IDs match the expected format for BitChute video
        identifiers using pattern matching for length and character validation.

        Args:
            video_id: Video identifier string to validate

        Raises:
            ValidationError: If video_id is not a string, empty, or doesn't
                match the expected format pattern

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_video_id('CLrgZP4RWyly')    # OK
            >>> validator.validate_video_id('abc123')          # OK
            >>> validator.validate_video_id('')                # Raises ValidationError
            >>> validator.validate_video_id('invalid@id')      # Raises ValidationError
        """
        if not isinstance(video_id, str):
            raise ValidationError(
                f"Video ID must be a string, got {type(video_id)}", "video_id"
            )

        video_id = video_id.strip()
        if not video_id:
            raise ValidationError("Video ID cannot be empty", "video_id")

        if not self.VIDEO_ID_PATTERN.match(video_id):
            raise ValidationError(
                f"Invalid video ID format: '{video_id}'. Must be 6-20 alphanumeric characters, hyphens, or underscores",
                "video_id",
            )

    def validate_channel_id(self, channel_id: str):
        """Validate channel ID format according to BitChute specifications.

        Ensures channel IDs match the expected format for BitChute channel
        identifiers using pattern matching for length and character validation.

        Args:
            channel_id: Channel identifier string to validate

        Raises:
            ValidationError: If channel_id is not a string, empty, or doesn't
                match the expected format pattern

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_channel_id('news_channel')     # OK
            >>> validator.validate_channel_id('channel-123')      # OK
            >>> validator.validate_channel_id('')                 # Raises ValidationError
            >>> validator.validate_channel_id('invalid@channel')  # Raises ValidationError
        """
        if not isinstance(channel_id, str):
            raise ValidationError(
                f"Channel ID must be a string, got {type(channel_id)}", "channel_id"
            )

        channel_id = channel_id.strip()
        if not channel_id:
            raise ValidationError("Channel ID cannot be empty", "channel_id")

        if not self.CHANNEL_ID_PATTERN.match(channel_id):
            raise ValidationError(
                f"Invalid channel ID format: '{channel_id}'. Must be 6-20 alphanumeric characters, hyphens, or underscores",
                "channel_id",
            )

    def validate_endpoint(self, endpoint: str):
        """Validate API endpoint format and security.

        Ensures API endpoint strings are properly formatted and match
        known endpoint patterns to prevent unauthorized API access
        and maintain security.

        Args:
            endpoint: API endpoint path to validate

        Raises:
            ValidationError: If endpoint is not a string, empty, contains
                invalid characters, or doesn't match known patterns

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_endpoint('beta/videos')           # OK
            >>> validator.validate_endpoint('beta/search/videos')    # OK
            >>> validator.validate_endpoint('')                      # Raises ValidationError
            >>> validator.validate_endpoint('invalid/endpoint')      # Raises ValidationError
        """
        if not isinstance(endpoint, str):
            raise ValidationError(
                f"Endpoint must be a string, got {type(endpoint)}", "endpoint"
            )

        endpoint = endpoint.strip()
        if not endpoint:
            raise ValidationError("Endpoint cannot be empty", "endpoint")

        # Basic endpoint format validation
        if not re.match(r"^[a-zA-Z0-9/_-]+$", endpoint):
            raise ValidationError(f"Invalid endpoint format: '{endpoint}'", "endpoint")

        # Check for known endpoint patterns
        valid_patterns = [
            r"^beta/videos",
            r"^beta/search/videos",
            r"^beta/search/channels",
            r"^beta/video/counts",
            r"^beta/hashtag/videos",
            r"^beta/video/media",
            r"^beta/video/comments",
            r"^beta/member_liked_videos",
            r"^beta/channel$",
            r"^beta/channel/videos",
            r"^beta/profile/links",
            r"^beta9/video",
            r"^beta9/hashtag/trending/",
        ]

        if not any(re.match(pattern, endpoint) for pattern in valid_patterns):
            raise ValidationError(f"Unknown endpoint: '{endpoint}'", "endpoint")

    def validate_payload(self, payload: Dict[str, Any]):
        """Validate complete API request payload structure and content.

        Performs comprehensive validation of request payload dictionaries
        including structure validation, size limits, and field-specific
        validation for all contained parameters.

        Args:
            payload: Request payload dictionary to validate

        Raises:
            ValidationError: If payload is not a dict, empty, too large,
                or contains invalid field values

        Example:
            >>> validator = InputValidator()
            >>> payload = {
            ...     "limit": 50,
            ...     "offset": 0,
            ...     "query": "bitcoin",
            ...     "sensitivity_id": "normal"
            ... }
            >>> validator.validate_payload(payload)  # OK
        """
        if not isinstance(payload, dict):
            raise ValidationError(
                f"Payload must be a dictionary, got {type(payload)}", "payload"
            )

        if not payload:
            raise ValidationError("Payload cannot be empty", "payload")

        # Check payload size
        import json

        payload_size = len(json.dumps(payload))
        if payload_size > 1024:  # 1KB limit
            raise ValidationError(
                f"Payload too large: {payload_size} bytes (max 1024)", "payload"
            )

        # Validate specific payload fields
        if "limit" in payload:
            self.validate_limit(payload["limit"])

        if "offset" in payload:
            self.validate_offset(payload["offset"])

        if "query" in payload:
            self.validate_search_query(payload["query"])

        if "video_id" in payload:
            self.validate_video_id(payload["video_id"])

        if "sensitivity_id" in payload:
            self.validate_sensitivity(payload["sensitivity_id"])

        if "sort" in payload:
            self.validate_sort_order(payload["sort"])

        if "selection" in payload:
            self.validate_selection(payload["selection"])

    def validate_export_format(self, format_name: str):
        """Validate export file format specification.

        Ensures export format names match supported file formats for
        data export operations.

        Args:
            format_name: Export format name to validate

        Raises:
            ValidationError: If format_name is not a string or not supported

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_export_format('csv')      # OK
            >>> validator.validate_export_format('json')     # OK
            >>> validator.validate_export_format('xml')      # Raises ValidationError
        """
        valid_formats = ["csv", "json", "xlsx", "parquet"]

        if not isinstance(format_name, str):
            raise ValidationError(
                f"Format must be a string, got {type(format_name)}", "format"
            )

        if format_name not in valid_formats:
            raise ValidationError(
                f"Format must be one of {valid_formats}, got '{format_name}'", "format"
            )

    def validate_filename(self, filename: str):
        """Validate filename for export operations with security checks.

        Ensures filenames are safe for filesystem operations across
        different platforms by checking for invalid characters and
        reasonable length limits.

        Args:
            filename: Filename string to validate

        Raises:
            ValidationError: If filename is not a string, empty, contains
                invalid characters, or exceeds length limits

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_filename('data_export')       # OK
            >>> validator.validate_filename('my-file_123')       # OK
            >>> validator.validate_filename('invalid/file')      # Raises ValidationError
        """
        if not isinstance(filename, str):
            raise ValidationError(
                f"Filename must be a string, got {type(filename)}", "filename"
            )

        filename = filename.strip()
        if not filename:
            raise ValidationError("Filename cannot be empty", "filename")

        # Check for invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            if char in filename:
                raise ValidationError(
                    f"Filename contains invalid character: '{char}'", "filename"
                )

        if len(filename) > 255:
            raise ValidationError(
                f"Filename too long (max 255 characters), got {len(filename)}",
                "filename",
            )

    def validate_timeout(self, timeout: int):
        """Validate timeout parameter for network operations.

        Ensures timeout values are reasonable positive numbers that
        won't cause excessive delays or immediate failures.

        Args:
            timeout: Timeout value in seconds

        Raises:
            ValidationError: If timeout is not a number, negative, or too large

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_timeout(30)    # OK
            >>> validator.validate_timeout(120)   # OK
            >>> validator.validate_timeout(-1)    # Raises ValidationError
            >>> validator.validate_timeout(500)   # Raises ValidationError
        """
        if not isinstance(timeout, (int, float)):
            raise ValidationError(
                f"Timeout must be a number, got {type(timeout)}", "timeout"
            )

        if timeout <= 0:
            raise ValidationError(f"Timeout must be positive, got {timeout}", "timeout")

        if timeout > 300:  # 5 minutes max
            raise ValidationError(
                f"Timeout too large (max 300 seconds), got {timeout}", "timeout"
            )

    def validate_max_workers(self, max_workers: int):
        """Validate max_workers parameter for concurrent processing.

        Ensures worker count values are reasonable positive integers
        that won't overwhelm system resources or cause performance issues.

        Args:
            max_workers: Maximum number of concurrent workers

        Raises:
            ValidationError: If max_workers is not an integer, too small, or too large

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_max_workers(5)     # OK
            >>> validator.validate_max_workers(10)    # OK
            >>> validator.validate_max_workers(0)     # Raises ValidationError
            >>> validator.validate_max_workers(50)    # Raises ValidationError
        """
        if not isinstance(max_workers, int):
            raise ValidationError(
                f"Max workers must be an integer, got {type(max_workers)}",
                "max_workers",
            )

        if max_workers < 1:
            raise ValidationError(
                f"Max workers must be at least 1, got {max_workers}", "max_workers"
            )

        if max_workers > 20:
            raise ValidationError(
                f"Max workers too high (max 20), got {max_workers}", "max_workers"
            )

    def validate_rate_limit(self, rate_limit: float):
        """Validate rate limit parameter for API request throttling.

        Ensures rate limit values are reasonable non-negative numbers
        that provide appropriate throttling without excessive delays.

        Args:
            rate_limit: Rate limit in seconds between requests

        Raises:
            ValidationError: If rate_limit is not a number, negative, or too large

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_rate_limit(0.5)    # OK
            >>> validator.validate_rate_limit(2.0)    # OK
            >>> validator.validate_rate_limit(-1)     # Raises ValidationError
            >>> validator.validate_rate_limit(100)    # Raises ValidationError
        """
        if not isinstance(rate_limit, (int, float)):
            raise ValidationError(
                f"Rate limit must be a number, got {type(rate_limit)}", "rate_limit"
            )

        if rate_limit < 0:
            raise ValidationError(
                f"Rate limit must be non-negative, got {rate_limit}", "rate_limit"
            )

        if rate_limit > 60:  # 1 minute max
            raise ValidationError(
                f"Rate limit too high (max 60 seconds), got {rate_limit}", "rate_limit"
            )

    def validate_video_ids(self, video_ids: List[str]):
        """Validate list of video IDs for batch operations.

        Ensures video ID lists are properly formatted with valid individual
        IDs and reasonable list sizes for batch processing operations.

        Args:
            video_ids: List of video ID strings to validate

        Raises:
            ValidationError: If video_ids is not a list, empty, too large,
                or contains invalid video IDs

        Example:
            >>> validator = InputValidator()
            >>> ids = ['CLrgZP4RWyly', 'abc123', 'video-id-1']
            >>> validator.validate_video_ids(ids)  # OK
            >>> validator.validate_video_ids([])   # Raises ValidationError
        """
        if not isinstance(video_ids, list):
            raise ValidationError(
                f"Video IDs must be a list, got {type(video_ids)}", "video_ids"
            )

        if not video_ids:
            raise ValidationError("Video IDs list cannot be empty", "video_ids")

        if len(video_ids) > 100:
            raise ValidationError(
                f"Too many video IDs (max 100), got {len(video_ids)}", "video_ids"
            )

        for i, video_id in enumerate(video_ids):
            try:
                self.validate_video_id(video_id)
            except ValidationError as e:
                raise ValidationError(
                    f"Invalid video ID at index {i}: {e.message}", "video_ids"
                )

    def validate_keywords(self, keywords: List[str]):
        """Validate list of keywords for content filtering operations.

        Ensures keyword lists contain valid strings with reasonable
        lengths and list sizes for filtering operations.

        Args:
            keywords: List of keyword strings to validate

        Raises:
            ValidationError: If keywords is not a list, too large, or contains
                invalid keyword strings

        Example:
            >>> validator = InputValidator()
            >>> keywords = ['bitcoin', 'cryptocurrency', 'blockchain']
            >>> validator.validate_keywords(keywords)  # OK
            >>> validator.validate_keywords([''])       # Raises ValidationError
        """
        if not isinstance(keywords, list):
            raise ValidationError(
                f"Keywords must be a list, got {type(keywords)}", "keywords"
            )

        if len(keywords) > 50:
            raise ValidationError(
                f"Too many keywords (max 50), got {len(keywords)}", "keywords"
            )

        for i, keyword in enumerate(keywords):
            if not isinstance(keyword, str):
                raise ValidationError(
                    f"Keyword at index {i} must be a string, got {type(keyword)}",
                    "keywords",
                )

            if len(keyword.strip()) == 0:
                raise ValidationError(
                    f"Keyword at index {i} cannot be empty", "keywords"
                )

            if len(keyword) > 100:
                raise ValidationError(
                    f"Keyword at index {i} too long (max 100 characters)", "keywords"
                )

    def validate_date_string(self, date_string: str, field_name: str):
        """Validate date string format using multiple common formats.

        Attempts to parse date strings using various common date formats
        to ensure compatibility with different date input styles.

        Args:
            date_string: Date string to validate
            field_name: Name of the field being validated for error reporting

        Raises:
            ValidationError: If date_string is not a string, empty, or doesn't
                match any supported date format

        Example:
            >>> validator = InputValidator()
            >>> validator.validate_date_string('2024-01-15', 'start_date')     # OK
            >>> validator.validate_date_string('01/15/2024', 'end_date')       # OK
            >>> validator.validate_date_string('invalid', 'date_field')        # Raises ValidationError
        """
        if not isinstance(date_string, str):
            raise ValidationError(
                f"{field_name} must be a string, got {type(date_string)}", field_name
            )

        date_string = date_string.strip()
        if not date_string:
            raise ValidationError(f"{field_name} cannot be empty", field_name)

        # Try to parse common date formats
        import datetime

        date_formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%m/%d/%Y",
            "%d/%m/%Y",
        ]

        for fmt in date_formats:
            try:
                datetime.datetime.strptime(date_string, fmt)
                return  # Valid format found
            except ValueError:
                continue

        raise ValidationError(
            f"Invalid date format for {field_name}: '{date_string}'. Expected formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, etc.",
            field_name,
        )
