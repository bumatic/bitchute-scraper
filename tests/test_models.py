"""
Tests for data models
"""

import pytest
from datetime import datetime
from bitchute.models import Video, Channel, Hashtag


class TestVideoModel:
    """Test Video data model"""
    
    def test_video_basic_properties(self):
        """Test basic video properties"""
        video = Video(
            id="test123",
            title="Test Video",
            view_count=1000,
            like_count=100,
            dislike_count=10,
            duration="10:30"
        )
        
        assert video.id == "test123"
        assert video.title == "Test Video"
        assert video.view_count == 1000
        assert video.like_count == 100
        assert video.dislike_count == 10
        assert video.duration == "10:30"
    
    def test_video_computed_properties(self):
        """Test computed properties"""
        video = Video(
            view_count=1000,
            like_count=100,
            dislike_count=10,
            duration="10:30"
        )
        
        # Test engagement rate: (likes + dislikes) / views
        assert video.engagement_rate == 0.11
        
        # Test like ratio: likes / (likes + dislikes)
        assert abs(video.like_ratio - 0.909) < 0.01
        
        # Test duration conversion: 10:30 = 630 seconds
        assert video.duration_seconds == 630
    
    def test_video_edge_cases(self):
        """Test edge cases for video model"""
        # Zero values
        video = Video(view_count=0, like_count=0, dislike_count=0)
        assert video.engagement_rate == 0.0
        assert video.like_ratio == 0.0
        assert video.duration_seconds == 0
        
        # Empty duration
        video = Video(duration="")
        assert video.duration_seconds == 0
    
    def test_video_url_generation(self):
        """Test automatic URL generation"""
        video = Video(id="test123")
        assert video.video_url == "https://www.bitchute.com/video/test123/"
        
        # Test with empty ID
        video = Video(id="")
        assert video.video_url == ""


class TestChannelModel:
    """Test Channel data model"""
    
    def test_channel_basic_properties(self):
        """Test basic channel properties"""
        channel = Channel(
            id="channel123",
            name="Test Channel",
            video_count=50,
            subscriber_count="1.2K",
            view_count=100000
        )
        
        assert channel.id == "channel123"
        assert channel.name == "Test Channel"
        assert channel.video_count == 50
        assert channel.subscriber_count == "1.2K"
        assert channel.view_count == 100000
    
    def test_subscriber_count_parsing(self):
        """Test subscriber count parsing"""
        test_cases = [
            ("1.2K", 1200),
            ("500", 500),
            ("2.5M", 2500000),
            ("10k", 10000),  # Lowercase
            ("invalid", 0),
            ("", 0),
        ]
        
        for input_val, expected in test_cases:
            channel = Channel(subscriber_count=input_val)
            assert channel.subscriber_count_numeric == expected
    
    def test_channel_url_generation(self):
        """Test automatic channel URL generation"""
        channel = Channel(id="channel123")
        assert channel.channel_url == "https://www.bitchute.com/channel/channel123/"


class TestHashtagModel:
    """Test Hashtag data model"""
    
    def test_hashtag_basic_properties(self):
        """Test basic hashtag properties"""
        hashtag = Hashtag(name="test", rank=1)
        
        assert hashtag.name == "test"
        assert hashtag.rank == 1
    
    def test_hashtag_name_processing(self):
        """Test hashtag name processing"""
        # Test without # prefix
        hashtag = Hashtag(name="test")
        assert hashtag.clean_name == "test"
        assert hashtag.formatted_name == "#test"
        
        # Test with # prefix
        hashtag = Hashtag(name="#test")
        assert hashtag.clean_name == "test"
        assert hashtag.formatted_name == "#test"
    
    def test_hashtag_url_generation(self):
        """Test hashtag URL generation"""
        hashtag = Hashtag(name="test")
        assert hashtag.url == "https://www.bitchute.com/hashtag/test/"
        
        hashtag = Hashtag(name="#test")
        assert hashtag.url == "https://www.bitchute.com/hashtag/test/"
