"""
Tests for input validation functionality
"""

import pytest
from bitchute.validators import InputValidator
from bitchute.exceptions import ValidationError


class TestInputValidator:
    """Test input validation functionality"""
    
    def setup_method(self):
        self.validator = InputValidator()
    
    def test_validate_limit_valid(self):
        """Test valid limit validation"""
        self.validator.validate_limit(10)
        self.validator.validate_limit(50, max_limit=100)
        self.validator.validate_limit(1, min_limit=1)
        self.validator.validate_limit(100, max_limit=100)
    
    def test_validate_limit_invalid(self):
        """Test invalid limit validation"""
        with pytest.raises(ValidationError, match="Limit must be an integer"):
            self.validator.validate_limit("10")
        
        with pytest.raises(ValidationError, match="Limit must be at least"):
            self.validator.validate_limit(0)
        
        with pytest.raises(ValidationError, match="Limit must be at most"):
            self.validator.validate_limit(101, max_limit=100)
        
        with pytest.raises(ValidationError):
            self.validator.validate_limit(-5)
    
    def test_validate_offset(self):
        """Test offset validation"""
        self.validator.validate_offset(0)
        self.validator.validate_offset(100)
        self.validator.validate_offset(1000)
        
        with pytest.raises(ValidationError, match="Offset must be non-negative"):
            self.validator.validate_offset(-1)
        
        with pytest.raises(ValidationError, match="Offset must be an integer"):
            self.validator.validate_offset("0")
        
        with pytest.raises(ValidationError):
            self.validator.validate_offset(3.14)
    
    def test_validate_timeframe(self):
        """Test timeframe validation"""
        valid_timeframes = ['day', 'week', 'month']
        for timeframe in valid_timeframes:
            self.validator.validate_timeframe(timeframe)
        
        invalid_timeframes = ['year', 'hour', 'minute', 123, None, '']
        for timeframe in invalid_timeframes:
            with pytest.raises(ValidationError):
                self.validator.validate_timeframe(timeframe)
    
    def test_validate_search_query(self):
        """Test search query validation"""
        # Valid queries
        self.validator.validate_search_query("climate change")
        self.validator.validate_search_query("test")
        self.validator.validate_search_query("a" * 50)  # Max reasonable length
        
        # Invalid queries
        with pytest.raises(ValidationError, match="Query cannot be empty"):
            self.validator.validate_search_query("")
        
        with pytest.raises(ValidationError, match="Query cannot be empty"):
            self.validator.validate_search_query("   ")  # Only spaces
        
        with pytest.raises(ValidationError, match="Query too long"):
            self.validator.validate_search_query("a" * 101)
        
        with pytest.raises(ValidationError, match="Query must be a string"):
            self.validator.validate_search_query(123)
    
    def test_validate_video_id(self):
        """Test video ID validation"""
        # Valid video IDs
        valid_ids = [
            "CLrgZP4RWyly",
            "abc123def456",
            "test_video-123",
            "a" * 12  # Minimum length
        ]
        for video_id in valid_ids:
            self.validator.validate_video_id(video_id)
        
        # Invalid video IDs
        with pytest.raises(ValidationError, match="Video ID cannot be empty"):
            self.validator.validate_video_id("")
        
        with pytest.raises(ValidationError, match="Invalid video ID format"):
            self.validator.validate_video_id("abc")  # Too short
        
        with pytest.raises(ValidationError, match="Invalid video ID format"):
            self.validator.validate_video_id("a" * 25)  # Too long
        
        with pytest.raises(ValidationError, match="Invalid video ID format"):
            self.validator.validate_video_id("abc@123")  # Invalid characters
