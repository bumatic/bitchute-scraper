"""
BitChute Scraper Input Validators
"""

import re
from typing import Any, Dict, List
from .exceptions import ValidationError


class InputValidator:
    """Validates inputs for BitChute API requests"""
    
    # Valid values for various parameters
    VALID_TIMEFRAMES = ['day', 'week', 'month']
    VALID_SENSITIVITIES = ['normal', 'nsfw', 'nsfl']
    VALID_SORT_ORDERS = ['new', 'relevant', 'views']
    VALID_SELECTIONS = ['trending-day', 'trending-week', 'trending-month', 'popular', 'all']
    
    # Regex patterns
    VIDEO_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{8,20}$')
    CHANNEL_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{8,20}$')
    
    def validate_limit(self, limit: int, max_limit: int = 100, min_limit: int = 1):
        """Validate limit parameter"""
        if not isinstance(limit, int):
            raise ValidationError(f"Limit must be an integer, got {type(limit)}", "limit")
        
        if limit < min_limit:
            raise ValidationError(f"Limit must be at least {min_limit}, got {limit}", "limit")
        
        if limit > max_limit:
            raise ValidationError(f"Limit must be at most {max_limit}, got {limit}", "limit")
    
    def validate_offset(self, offset: int):
        """Validate offset parameter"""
        if not isinstance(offset, int):
            raise ValidationError(f"Offset must be an integer, got {type(offset)}", "offset")
        
        if offset < 0:
            raise ValidationError(f"Offset must be non-negative, got {offset}", "offset")
    
    def validate_timeframe(self, timeframe: str):
        """Validate timeframe parameter"""
        if not isinstance(timeframe, str):
            raise ValidationError(f"Timeframe must be a string, got {type(timeframe)}", "timeframe")
        
        if timeframe not in self.VALID_TIMEFRAMES:
            raise ValidationError(
                f"Timeframe must be one of {self.VALID_TIMEFRAMES}, got '{timeframe}'",
                "timeframe"
            )
    
    def validate_sensitivity(self, sensitivity: str):
        """Validate sensitivity parameter"""
        if not isinstance(sensitivity, str):
            raise ValidationError(f"Sensitivity must be a string, got {type(sensitivity)}", "sensitivity")
        
        if sensitivity not in self.VALID_SENSITIVITIES:
            raise ValidationError(
                f"Sensitivity must be one of {self.VALID_SENSITIVITIES}, got '{sensitivity}'",
                "sensitivity"
            )
    
    def validate_sort_order(self, sort_order: str):
        """Validate sort order parameter"""
        if not isinstance(sort_order, str):
            raise ValidationError(f"Sort order must be a string, got {type(sort_order)}", "sort_order")
        
        if sort_order not in self.VALID_SORT_ORDERS:
            raise ValidationError(
                f"Sort order must be one of {self.VALID_SORT_ORDERS}, got '{sort_order}'",
                "sort_order"
            )
    
    def validate_selection(self, selection: str):
        """Validate selection parameter"""
        if not isinstance(selection, str):
            raise ValidationError(f"Selection must be a string, got {type(selection)}", "selection")
        
        if selection not in self.VALID_SELECTIONS:
            raise ValidationError(
                f"Selection must be one of {self.VALID_SELECTIONS}, got '{selection}'",
                "selection"
            )
    
    def validate_search_query(self, query: str):
        """Validate search query"""
        if not isinstance(query, str):
            raise ValidationError(f"Query must be a string, got {type(query)}", "query")
        
        query = query.strip()
        if not query:
            raise ValidationError("Query cannot be empty", "query")
        
        if len(query) > 100:
            raise ValidationError(f"Query too long (max 100 characters), got {len(query)}", "query")
        
        # Check for suspicious patterns
        if query.count(' ') > 20:
            raise ValidationError("Query contains too many spaces", "query")
    
    def validate_video_id(self, video_id: str):
        """Validate video ID format"""
        if not isinstance(video_id, str):
            raise ValidationError(f"Video ID must be a string, got {type(video_id)}", "video_id")
        
        video_id = video_id.strip()
        if not video_id:
            raise ValidationError("Video ID cannot be empty", "video_id")
        
        if not self.VIDEO_ID_PATTERN.match(video_id):
            raise ValidationError(
                f"Invalid video ID format: '{video_id}'. Must be 8-20 alphanumeric characters, hyphens, or underscores",
                "video_id"
            )
    
    def validate_channel_id(self, channel_id: str):
        """Validate channel ID format"""
        if not isinstance(channel_id, str):
            raise ValidationError(f"Channel ID must be a string, got {type(channel_id)}", "channel_id")
        
        channel_id = channel_id.strip()
        if not channel_id:
            raise ValidationError("Channel ID cannot be empty", "channel_id")
        
        if not self.CHANNEL_ID_PATTERN.match(channel_id):
            raise ValidationError(
                f"Invalid channel ID format: '{channel_id}'. Must be 8-20 alphanumeric characters, hyphens, or underscores",
                "channel_id"
            )
    
    def validate_endpoint(self, endpoint: str):
        """Validate API endpoint"""
        if not isinstance(endpoint, str):
            raise ValidationError(f"Endpoint must be a string, got {type(endpoint)}", "endpoint")
        
        endpoint = endpoint.strip()
        if not endpoint:
            raise ValidationError("Endpoint cannot be empty", "endpoint")
        
        # Basic endpoint format validation
        if not re.match(r'^[a-zA-Z0-9/_-]+, endpoint):
            raise ValidationError(f"Invalid endpoint format: '{endpoint}'", "endpoint")
        
        # Check for common endpoint patterns
        valid_patterns = [
            r'^beta/videos,
            r'^beta/search/videos,
            r'^beta/search/channels,
            r'^beta/video/counts,
            r'^beta/video/media,
            r'^beta/member_liked_videos,
            r'^beta9/video,
            r'^beta9/hashtag/trending/
        ]
        
        if not any(re.match(pattern, endpoint) for pattern in valid_patterns):
            raise ValidationError(f"Unknown endpoint: '{endpoint}'", "endpoint")
    
    def validate_payload(self, payload: Dict[str, Any]):
        """Validate request payload"""
        if not isinstance(payload, dict):
            raise ValidationError(f"Payload must be a dictionary, got {type(payload)}", "payload")
        
        if not payload:
            raise ValidationError("Payload cannot be empty", "payload")
        
        # Check payload size
        import json
        payload_size = len(json.dumps(payload))
        if payload_size > 1024:  # 1KB limit
            raise ValidationError(f"Payload too large: {payload_size} bytes (max 1024)", "payload")
        
        # Validate specific payload fields
        if 'limit' in payload:
            self.validate_limit(payload['limit'])
        
        if 'offset' in payload:
            self.validate_offset(payload['offset'])
        
        if 'query' in payload:
            self.validate_search_query(payload['query'])
        
        if 'video_id' in payload:
            self.validate_video_id(payload['video_id'])
        
        if 'sensitivity_id' in payload:
            self.validate_sensitivity(payload['sensitivity_id'])
        
        if 'sort' in payload:
            self.validate_sort_order(payload['sort'])
        
        if 'selection' in payload:
            self.validate_selection(payload['selection'])
    
    def validate_export_format(self, format_name: str):
        """Validate export format"""
        valid_formats = ['csv', 'json', 'xlsx', 'parquet']
        
        if not isinstance(format_name, str):
            raise ValidationError(f"Format must be a string, got {type(format_name)}", "format")
        
        if format_name not in valid_formats:
            raise ValidationError(
                f"Format must be one of {valid_formats}, got '{format_name}'",
                "format"
            )
    
    def validate_filename(self, filename: str):
        """Validate filename for export"""
        if not isinstance(filename, str):
            raise ValidationError(f"Filename must be a string, got {type(filename)}", "filename")
        
        filename = filename.strip()
        if not filename:
            raise ValidationError("Filename cannot be empty", "filename")
        
        # Check for invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            if char in filename:
                raise ValidationError(f"Filename contains invalid character: '{char}'", "filename")
        
        if len(filename) > 255:
            raise ValidationError(f"Filename too long (max 255 characters), got {len(filename)}", "filename")
    
    def validate_timeout(self, timeout: int):
        """Validate timeout parameter"""
        if not isinstance(timeout, (int, float)):
            raise ValidationError(f"Timeout must be a number, got {type(timeout)}", "timeout")
        
        if timeout <= 0:
            raise ValidationError(f"Timeout must be positive, got {timeout}", "timeout")
        
        if timeout > 300:  # 5 minutes max
            raise ValidationError(f"Timeout too large (max 300 seconds), got {timeout}", "timeout")
    
    def validate_max_workers(self, max_workers: int):
        """Validate max_workers parameter for concurrent processing"""
        if not isinstance(max_workers, int):
            raise ValidationError(f"Max workers must be an integer, got {type(max_workers)}", "max_workers")
        
        if max_workers < 1:
            raise ValidationError(f"Max workers must be at least 1, got {max_workers}", "max_workers")
        
        if max_workers > 20:
            raise ValidationError(f"Max workers too high (max 20), got {max_workers}", "max_workers")
    
    def validate_rate_limit(self, rate_limit: float):
        """Validate rate limit parameter"""
        if not isinstance(rate_limit, (int, float)):
            raise ValidationError(f"Rate limit must be a number, got {type(rate_limit)}", "rate_limit")
        
        if rate_limit < 0:
            raise ValidationError(f"Rate limit must be non-negative, got {rate_limit}", "rate_limit")
        
        if rate_limit > 60:  # 1 minute max
            raise ValidationError(f"Rate limit too high (max 60 seconds), got {rate_limit}", "rate_limit")
    
    def validate_video_ids(self, video_ids: List[str]):
        """Validate list of video IDs"""
        if not isinstance(video_ids, list):
            raise ValidationError(f"Video IDs must be a list, got {type(video_ids)}", "video_ids")
        
        if not video_ids:
            raise ValidationError("Video IDs list cannot be empty", "video_ids")
        
        if len(video_ids) > 100:
            raise ValidationError(f"Too many video IDs (max 100), got {len(video_ids)}", "video_ids")
        
        for i, video_id in enumerate(video_ids):
            try:
                self.validate_video_id(video_id)
            except ValidationError as e:
                raise ValidationError(f"Invalid video ID at index {i}: {e.message}", "video_ids")
    
    def validate_keywords(self, keywords: List[str]):
        """Validate list of keywords for filtering"""
        if not isinstance(keywords, list):
            raise ValidationError(f"Keywords must be a list, got {type(keywords)}", "keywords")
        
        if len(keywords) > 50:
            raise ValidationError(f"Too many keywords (max 50), got {len(keywords)}", "keywords")
        
        for i, keyword in enumerate(keywords):
            if not isinstance(keyword, str):
                raise ValidationError(f"Keyword at index {i} must be a string, got {type(keyword)}", "keywords")
            
            if len(keyword.strip()) == 0:
                raise ValidationError(f"Keyword at index {i} cannot be empty", "keywords")
            
            if len(keyword) > 100:
                raise ValidationError(f"Keyword at index {i} too long (max 100 characters)", "keywords")
    
    def validate_date_string(self, date_string: str, field_name: str):
        """Validate date string format"""
        if not isinstance(date_string, str):
            raise ValidationError(f"{field_name} must be a string, got {type(date_string)}", field_name)
        
        date_string = date_string.strip()
        if not date_string:
            raise ValidationError(f"{field_name} cannot be empty", field_name)
        
        # Try to parse common date formats
        import datetime
        
        date_formats = [
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%m/%d/%Y',
            '%d/%m/%Y'
        ]
        
        for fmt in date_formats:
            try:
                datetime.datetime.strptime(date_string, fmt)
                return  # Valid format found
            except ValueError:
                continue
        
        raise ValidationError(
            f"Invalid date format for {field_name}: '{date_string}'. Expected formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, etc.",
            field_name
        )