"""
Test input validators
"""

import pytest
import json
from datetime import datetime

from bitchute.validators import InputValidator
from bitchute.exceptions import ValidationError


class TestInputValidator:
    """Test InputValidator class"""
    
    @pytest.fixture
    def validator(self):
        return InputValidator()
    
    def test_validator_constants(self, validator):
        """Test validator has correct constants"""
        assert 'day' in validator.VALID_TIMEFRAMES
        assert 'week' in validator.VALID_TIMEFRAMES
        assert 'month' in validator.VALID_TIMEFRAMES
        
        assert 'normal' in validator.VALID_SENSITIVITIES
        assert 'nsfw' in validator.VALID_SENSITIVITIES
        assert 'nsfl' in validator.VALID_SENSITIVITIES
        
        assert 'new' in validator.VALID_SORT_ORDERS
        assert 'old' in validator.VALID_SORT_ORDERS
        assert 'views' in validator.VALID_SORT_ORDERS
    
    def test_validate_limit_valid(self, validator):
        """Test valid limit values"""
        # Valid values
        validator.validate_limit(1)
        validator.validate_limit(50)
        validator.validate_limit(100)
        
        # Custom range
        validator.validate_limit(200, max_limit=500)
        validator.validate_limit(5, min_limit=5)
    
    def test_validate_limit_invalid(self, validator):
        """Test invalid limit values"""
        # Too small
        with pytest.raises(ValidationError) as exc:
            validator.validate_limit(0)
        assert "at least 1" in str(exc.value)
        
        # Too large
        with pytest.raises(ValidationError) as exc:
            validator.validate_limit(150)
        assert "at most 100" in str(exc.value)
        
        # Wrong type
        with pytest.raises(ValidationError) as exc:
            validator.validate_limit("50")
        assert "must be an integer" in str(exc.value)
        
        # Float
        with pytest.raises(ValidationError):
            validator.validate_limit(50.5)
    
    def test_validate_offset_valid(self, validator):
        """Test valid offset values"""
        validator.validate_offset(0)
        validator.validate_offset(100)
        validator.validate_offset(1000000)
    
    def test_validate_offset_invalid(self, validator):
        """Test invalid offset values"""
        # Negative
        with pytest.raises(ValidationError) as exc:
            validator.validate_offset(-1)
        assert "non-negative" in str(exc.value)
        
        # Wrong type
        with pytest.raises(ValidationError):
            validator.validate_offset("0")
    
    def test_validate_timeframe_valid(self, validator):
        """Test valid timeframe values"""
        validator.validate_timeframe("day")
        validator.validate_timeframe("week")
        validator.validate_timeframe("month")
    
    def test_validate_timeframe_invalid(self, validator):
        """Test invalid timeframe values"""
        # Invalid value
        with pytest.raises(ValidationError) as exc:
            validator.validate_timeframe("year")
        assert "one of ['day', 'week', 'month']" in str(exc.value)
        
        # Wrong type
        with pytest.raises(ValidationError):
            validator.validate_timeframe(1)
        
        # Case sensitive
        with pytest.raises(ValidationError):
            validator.validate_timeframe("DAY")
    
    def test_validate_sensitivity_valid(self, validator):
        """Test valid sensitivity values"""
        validator.validate_sensitivity("normal")
        validator.validate_sensitivity("nsfw")
        validator.validate_sensitivity("nsfl")
    
    def test_validate_sensitivity_invalid(self, validator):
        """Test invalid sensitivity values"""
        with pytest.raises(ValidationError) as exc:
            validator.validate_sensitivity("explicit")
        assert "one of ['normal', 'nsfw', 'nsfl']" in str(exc.value)
        
        with pytest.raises(ValidationError):
            validator.validate_sensitivity("")
    
    def test_validate_sort_order_valid(self, validator):
        """Test valid sort order values"""
        validator.validate_sort_order("new")
        validator.validate_sort_order("old")
        validator.validate_sort_order("views")
    
    def test_validate_sort_order_invalid(self, validator):
        """Test invalid sort order values"""
        with pytest.raises(ValidationError):
            validator.validate_sort_order("popularity")
        
        with pytest.raises(ValidationError):
            validator.validate_sort_order("newest")
    
    def test_validate_selection_valid(self, validator):
        """Test valid selection values"""
        validator.validate_selection("trending-day")
        validator.validate_selection("trending-week")
        validator.validate_selection("trending-month")
        validator.validate_selection("popular")
        validator.validate_selection("all")
    
    def test_validate_selection_invalid(self, validator):
        """Test invalid selection values"""
        with pytest.raises(ValidationError):
            validator.validate_selection("trending")
        
        with pytest.raises(ValidationError):
            validator.validate_selection("featured")
    
    def test_validate_search_query_valid(self, validator):
        """Test valid search queries"""
        validator.validate_search_query("bitcoin")
        validator.validate_search_query("climate change")
        validator.validate_search_query("a")  # Single character
        validator.validate_search_query("test " * 10)  # Multiple words
    
    def test_validate_search_query_invalid(self, validator):
        """Test invalid search queries"""
        # Empty
        with pytest.raises(ValidationError) as exc:
            validator.validate_search_query("")
        assert "cannot be empty" in str(exc.value)

        # Only spaces
        with pytest.raises(ValidationError):
            validator.validate_search_query("   ")

        # Too long
        with pytest.raises(ValidationError) as exc:
            validator.validate_search_query("a" * 101)
        assert "too long" in str(exc.value)

        # Too many spaces - create a string with more than 20 spaces
        with pytest.raises(ValidationError) as exc:
            validator.validate_search_query("a " * 22) 
        assert "too many spaces" in str(exc.value)
    
    def test_validate_video_id_valid(self, validator):
        """Test valid video IDs"""
        validator.validate_video_id("iSbiDDQ5sJk")
        validator.validate_video_id("test123ABC")
        validator.validate_video_id("video_id-123")
        validator.validate_video_id("a" * 20)  # Max length

    def test_validate_video_ids_valid(self, validator):
        """Test valid video ID lists"""
        validator.validate_video_ids(["iSbiDDQ5sJk"])
        validator.validate_video_ids(["RX5Ius1lwEkg", "ntFqxiV0u5FV", "Vq3po0k1AAyB"])  # Updated to valid format
        validator.validate_video_ids(["tmLJ1sm9GG8", "oG363NxBmGhi", "tenIadecLNk1"])
    
    def test_validate_video_id_invalid(self, validator):
        """Test invalid video IDs"""
        # Empty
        with pytest.raises(ValidationError):
            validator.validate_video_id("")
        
        # Too short
        with pytest.raises(ValidationError) as exc:
            validator.validate_video_id("abc")  # 3 chars
        assert "8-20 alphanumeric" in str(exc.value)
        
        # Too long
        with pytest.raises(ValidationError):
            validator.validate_video_id("a" * 21)
        
        # Invalid characters
        with pytest.raises(ValidationError):
            validator.validate_video_id("test@123")
        
        with pytest.raises(ValidationError):
            validator.validate_video_id("test#123")
        
        # Wrong type
        with pytest.raises(ValidationError):
            validator.validate_video_id(123)
    
    def test_validate_channel_id_valid(self, validator):
        """Test valid channel IDs"""
        validator.validate_channel_id("chan1234")
        validator.validate_channel_id("Channel_123")
        validator.validate_channel_id("test-channel-id")
    
    def test_validate_channel_id_invalid(self, validator):
        """Test invalid channel IDs"""
        # Similar rules as video ID
        with pytest.raises(ValidationError):
            validator.validate_channel_id("")
        
        with pytest.raises(ValidationError):
            validator.validate_channel_id("short")
        
        with pytest.raises(ValidationError):
            validator.validate_channel_id("invalid@channel")
    
    def test_validate_endpoint_valid(self, validator):
        """Test valid endpoints"""
        validator.validate_endpoint("beta/videos")
        validator.validate_endpoint("beta/search/videos")
        validator.validate_endpoint("beta/search/channels")
        validator.validate_endpoint("beta/video/counts")
        validator.validate_endpoint("beta/video/media")
        validator.validate_endpoint("beta9/video")
        validator.validate_endpoint("beta9/hashtag/trending/")
        validator.validate_endpoint("beta/channel")
        validator.validate_endpoint("beta/channel/videos")
        validator.validate_endpoint("beta/profile/links")
    
    def test_validate_endpoint_invalid(self, validator):
        """Test invalid endpoints"""
        # Empty
        with pytest.raises(ValidationError):
            validator.validate_endpoint("")
        
        # Invalid format
        with pytest.raises(ValidationError):
            validator.validate_endpoint("beta videos")
        
        with pytest.raises(ValidationError):
            validator.validate_endpoint("beta/videos?limit=10")
        
        # Unknown endpoint
        with pytest.raises(ValidationError) as exc:
            validator.validate_endpoint("unknown/endpoint")
        assert "Unknown endpoint" in str(exc.value)
        
        # Wrong type
        with pytest.raises(ValidationError):
            validator.validate_endpoint(123)
    
    def test_validate_payload_valid(self, validator):
        """Test valid payloads"""
        validator.validate_payload({"limit": 50})
        validator.validate_payload({"offset": 0, "limit": 20})
        validator.validate_payload({"query": "test", "sensitivity_id": "normal"})
        validator.validate_payload({"video_id": "test123abc"})
    
    def test_validate_payload_invalid(self, validator):
        """Test invalid payloads"""
        # Not a dict
        with pytest.raises(ValidationError):
            validator.validate_payload("invalid")
        
        # Empty
        with pytest.raises(ValidationError):
            validator.validate_payload({})
        
        # Too large
        large_payload = {"data": "x" * 2000}
        with pytest.raises(ValidationError) as exc:
            validator.validate_payload(large_payload)
        assert "too large" in str(exc.value)
        
        # Invalid nested values
        with pytest.raises(ValidationError):
            validator.validate_payload({"limit": 200})  # Too high
        
        with pytest.raises(ValidationError):
            validator.validate_payload({"offset": -1})  # Negative
    
    def test_validate_export_format_valid(self, validator):
        """Test valid export formats"""
        validator.validate_export_format("csv")
        validator.validate_export_format("json")
        validator.validate_export_format("xlsx")
        validator.validate_export_format("parquet")
    
    def test_validate_export_format_invalid(self, validator):
        """Test invalid export formats"""
        with pytest.raises(ValidationError):
            validator.validate_export_format("xml")
        
        with pytest.raises(ValidationError):
            validator.validate_export_format("txt")
        
        with pytest.raises(ValidationError):
            validator.validate_export_format("")
    
    def test_validate_filename_valid(self, validator):
        """Test valid filenames"""
        validator.validate_filename("output")
        validator.validate_filename("my_data_2024")
        validator.validate_filename("test-file-name")
        validator.validate_filename("a" * 255)  # Max length
    
    def test_validate_filename_invalid(self, validator):
        """Test invalid filenames"""
        # Empty
        with pytest.raises(ValidationError):
            validator.validate_filename("")
        
        # Invalid characters
        for char in '<>:"/\\|?*':
            with pytest.raises(ValidationError) as exc:
                validator.validate_filename(f"test{char}file")
            assert f"invalid character: '{char}'" in str(exc.value)
        
        # Too long
        with pytest.raises(ValidationError):
            validator.validate_filename("a" * 256)
    
    def test_validate_timeout_valid(self, validator):
        """Test valid timeout values"""
        validator.validate_timeout(1)
        validator.validate_timeout(30)
        validator.validate_timeout(300)
        validator.validate_timeout(0.5)  # Float allowed
    
    def test_validate_timeout_invalid(self, validator):
        """Test invalid timeout values"""
        # Zero or negative
        with pytest.raises(ValidationError):
            validator.validate_timeout(0)
        
        with pytest.raises(ValidationError):
            validator.validate_timeout(-1)
        
        # Too large
        with pytest.raises(ValidationError):
            validator.validate_timeout(301)
        
        # Wrong type
        with pytest.raises(ValidationError):
            validator.validate_timeout("30")
    
    def test_validate_max_workers_valid(self, validator):
        """Test valid max_workers values"""
        validator.validate_max_workers(1)
        validator.validate_max_workers(5)
        validator.validate_max_workers(10)
        validator.validate_max_workers(20)
    
    def test_validate_max_workers_invalid(self, validator):
        """Test invalid max_workers values"""
        # Too small
        with pytest.raises(ValidationError):
            validator.validate_max_workers(0)
        
        # Too large
        with pytest.raises(ValidationError):
            validator.validate_max_workers(21)
        
        # Wrong type
        with pytest.raises(ValidationError):
            validator.validate_max_workers(5.5)
        
        with pytest.raises(ValidationError):
            validator.validate_max_workers("5")
    
    def test_validate_rate_limit_valid(self, validator):
        """Test valid rate limit values"""
        validator.validate_rate_limit(0)
        validator.validate_rate_limit(0.5)
        validator.validate_rate_limit(1)
        validator.validate_rate_limit(60)
    
    def test_validate_rate_limit_invalid(self, validator):
        """Test invalid rate limit values"""
        # Negative
        with pytest.raises(ValidationError):
            validator.validate_rate_limit(-1)
        
        # Too high
        with pytest.raises(ValidationError):
            validator.validate_rate_limit(61)
        
        # Wrong type
        with pytest.raises(ValidationError):
            validator.validate_rate_limit("1")
    
    def test_validate_video_ids_valid(self, validator):
        """Test valid video ID lists"""
        validator.validate_video_ids(["test123abc"])
        validator.validate_video_ids(["video1", "video2", "video3"])
        validator.validate_video_ids(["a" * 20 for _ in range(100)])  # Max
    
    def test_validate_video_ids_invalid(self, validator):
        """Test invalid video ID lists"""
        # Not a list
        with pytest.raises(ValidationError):
            validator.validate_video_ids("test123")
        
        # Empty list
        with pytest.raises(ValidationError):
            validator.validate_video_ids([])
        
        # Too many
        with pytest.raises(ValidationError):
            validator.validate_video_ids(["id" for _ in range(101)])
        
        # Invalid ID in list
        with pytest.raises(ValidationError) as exc:
            validator.validate_video_ids(["valid123", "short", "valid456"])
        assert "index 1" in str(exc.value)
    
    def test_validate_keywords_valid(self, validator):
        """Test valid keyword lists"""
        validator.validate_keywords(["bitcoin"])
        validator.validate_keywords(["crypto", "blockchain", "defi"])
        validator.validate_keywords(["keyword" for _ in range(50)])  # Max
    
    def test_validate_keywords_invalid(self, validator):
        """Test invalid keyword lists"""
        # Not a list
        with pytest.raises(ValidationError):
            validator.validate_keywords("bitcoin")
        
        # Too many
        with pytest.raises(ValidationError):
            validator.validate_keywords(["kw" for _ in range(51)])
        
        # Empty keyword
        with pytest.raises(ValidationError) as exc:
            validator.validate_keywords(["valid", "  ", "also valid"])
        assert "index 1" in str(exc.value)
        
        # Non-string keyword
        with pytest.raises(ValidationError):
            validator.validate_keywords(["valid", 123, "valid"])
        
        # Too long keyword
        with pytest.raises(ValidationError):
            validator.validate_keywords(["a" * 101])
    
    def test_validate_date_string_valid(self, validator):
        """Test valid date strings"""
        validator.validate_date_string("2024-01-15", "start_date")
        validator.validate_date_string("2024-01-15 14:30:00", "end_date")
        validator.validate_date_string("2024-01-15T14:30:00", "date")
        validator.validate_date_string("2024-01-15T14:30:00Z", "timestamp")
        validator.validate_date_string("01/15/2024", "date")
        validator.validate_date_string("15/01/2024", "date")
    
    def test_validate_date_string_invalid(self, validator):
        """Test invalid date strings"""
        # Not a string
        with pytest.raises(ValidationError):
            validator.validate_date_string(123, "date")
        
        # Empty
        with pytest.raises(ValidationError):
            validator.validate_date_string("", "date")
        
        # Invalid format
        with pytest.raises(ValidationError) as exc:
            validator.validate_date_string("2024/01/15", "date")
        assert "Invalid date format" in str(exc.value)
        
        with pytest.raises(ValidationError):
            validator.validate_date_string("not a date", "date")
        
        with pytest.raises(ValidationError):
            validator.validate_date_string("2024-13-01", "date")  # Invalid month


class TestValidatorFieldNames:
    """Test that field names are properly included in errors"""
    
    @pytest.fixture
    def validator(self):
        return InputValidator()
    
    def test_field_names_in_errors(self, validator):
        """Test that validation errors include field names"""
        # Limit
        with pytest.raises(ValidationError) as exc:
            validator.validate_limit(0)
        assert exc.value.field == "limit"
        
        # Query
        with pytest.raises(ValidationError) as exc:
            validator.validate_search_query("")
        assert exc.value.field == "query"
        
        # Video ID
        with pytest.raises(ValidationError) as exc:
            validator.validate_video_id("bad")
        assert exc.value.field == "video_id"
        
        # Date string with custom field
        with pytest.raises(ValidationError) as exc:
            validator.validate_date_string("invalid", "custom_date")
        assert exc.value.field == "custom_date"


class TestValidatorEdgeCases:
    """Test edge cases for validators"""
    
    @pytest.fixture
    def validator(self):
        return InputValidator()
    
    def test_unicode_handling(self, validator):
        """Test validation with unicode characters"""
        # Search query with unicode
        validator.validate_search_query("bitcoin 比特币")
        validator.validate_search_query("🚀 crypto")
        
        # Filename with unicode
        validator.validate_filename("output_测试")
        
        # But not in IDs
        with pytest.raises(ValidationError):
            validator.validate_video_id("test比特币123")
    
    def test_boundary_values(self, validator):
        """Test boundary values"""
        # Exactly at limits
        validator.validate_limit(1, min_limit=1)
        validator.validate_limit(100, max_limit=100)
        validator.validate_search_query("a" * 100)  # Exactly 100 chars
        validator.validate_filename("a" * 255)  # Exactly 255 chars
        
        # Just over limits
        with pytest.raises(ValidationError):
            validator.validate_search_query("a" * 101)
        
        with pytest.raises(ValidationError):
            validator.validate_filename("a" * 256)
    
    def test_payload_nested_validation(self, validator):
        """Test payload validation with nested fields"""
        # Complex valid payload
        complex_payload = {
            "limit": 50,
            "offset": 100,
            "query": "test search",
            "video_id": "valid123id",
            "sensitivity_id": "nsfw",
            "sort": "views"
        }
        validator.validate_payload(complex_payload)
        
        # Multiple validation errors
        invalid_payload = {
            "limit": 200,  # Too high
            "offset": -1,  # Negative
            "query": "",  # Empty
            "video_id": "bad",  # Too short
            "sensitivity_id": "invalid",  # Invalid value
            "sort": "popularity"  # Invalid value
        }
        
        # Should fail on first invalid field
        with pytest.raises(ValidationError):
            validator.validate_payload(invalid_payload)