"""
Test data models
"""

import pytest
from datetime import datetime
from dataclasses import asdict

from bitchute.models import Video, Channel, Hashtag, APIStats, SearchResult


class TestVideoModel:
    """Test Video data model"""
    
    def test_video_initialization_minimal(self):
        """Test Video with minimal data"""
        video = Video(id="test123", title="Test Video")
        
        assert video.id == "test123"
        assert video.title == "Test Video"
        assert video.view_count == 0
        assert video.like_count == 0
        assert video.dislike_count == 0
        assert video.duration == ""
        assert video.scrape_timestamp > 0
    
    def test_video_initialization_complete(self):
        """Test Video with complete data"""
        video = Video(
            id="test123",
            title="Test Video",
            description="Test description",
            view_count=1500,
            like_count=100,
            dislike_count=10,
            duration="10:30",
            thumbnail_url="https://example.com/thumb.jpg",
            channel_id="ch123",
            channel_name="Test Channel",
            category="education",
            sensitivity="normal",
            hashtags=["#test", "#example"],
            upload_date="2024-01-01T00:00:00Z",
            is_short=False
        )
        
        assert video.id == "test123"
        assert video.title == "Test Video"
        assert video.view_count == 1500
        assert video.like_count == 100
        assert video.dislike_count == 10
        assert video.duration == "10:30"
        assert video.channel_name == "Test Channel"
        assert len(video.hashtags) == 2
        assert "#test" in video.hashtags
    
    def test_video_post_init(self):
        """Test Video post-initialization"""
        video = Video(id="test123")
        
        # Should auto-generate video URL
        assert video.video_url == "https://www.bitchute.com/video/test123/"
        
        # Should have timestamp
        assert video.scrape_timestamp > 0
        assert isinstance(video.scrape_timestamp, float)
    
    def test_video_engagement_rate(self):
        """Test video engagement rate calculation"""
        # Video with engagement
        video = Video(
            id="test123",
            view_count=1000,
            like_count=80,
            dislike_count=20
        )
        
        assert video.engagement_rate == 0.1  # (80 + 20) / 1000
        
        # Video with no views
        video_no_views = Video(id="test456", view_count=0, like_count=0)
        assert video_no_views.engagement_rate == 0.0
    
    def test_video_like_ratio(self):
        """Test video like ratio calculation"""
        # Normal case
        video = Video(
            id="test123",
            like_count=90,
            dislike_count=10
        )
        assert video.like_ratio == 0.9  # 90 / (90 + 10)
        
        # No reactions
        video_no_reactions = Video(id="test456")
        assert video_no_reactions.like_ratio == 0.0
        
        # Only likes
        video_only_likes = Video(id="test789", like_count=100, dislike_count=0)
        assert video_only_likes.like_ratio == 1.0
    
    def test_video_duration_seconds(self):
        """Test duration conversion to seconds"""
        # MM:SS format
        video1 = Video(id="test1", duration="5:30")
        assert video1.duration_seconds == 330  # 5*60 + 30
        
        # HH:MM:SS format
        video2 = Video(id="test2", duration="1:23:45")
        assert video2.duration_seconds == 5025  # 1*3600 + 23*60 + 45
        
        # Invalid format
        video3 = Video(id="test3", duration="invalid")
        assert video3.duration_seconds == 0
        
        # Empty duration
        video4 = Video(id="test4", duration="")
        assert video4.duration_seconds == 0
    
    def test_video_to_dict(self):
        """Test video conversion to dictionary"""
        video = Video(
            id="test123",
            title="Test Video",
            view_count=1000,
            like_count=80,
            dislike_count=20,
            duration="5:30"
        )
        
        data = video.to_dict()
        
        assert isinstance(data, dict)
        assert data['id'] == "test123"
        assert data['title'] == "Test Video"
        assert data['view_count'] == 1000
        assert data['engagement_rate'] == 0.1
        assert data['like_ratio'] == 0.8
        assert data['duration_seconds'] == 330
    
    def test_video_dataclass_conversion(self):
        """Test dataclass conversion"""
        video = Video(id="test123", title="Test")
        data = asdict(video)
        
        assert isinstance(data, dict)
        assert 'id' in data
        assert 'title' in data
        assert 'scrape_timestamp' in data


class TestChannelModel:
    """Test Channel data model"""
    
    def test_channel_initialization_minimal(self):
        """Test Channel with minimal data"""
        channel = Channel(id="ch123", name="Test Channel")
        
        assert channel.id == "ch123"
        assert channel.name == "Test Channel"
        assert channel.video_count == 0
        assert channel.view_count == 0
        assert channel.subscriber_count == ""
        assert channel.scrape_timestamp > 0
    
    def test_channel_initialization_complete(self):
        """Test Channel with complete data"""
        channel = Channel(
            id="ch123",
            name="Test Channel",
            description="Test description",
            url_slug="test-channel",
            video_count=150,
            subscriber_count="5.2K",
            view_count=250000,
            created_date="2022-01-01T00:00:00Z",
            last_video_published="2024-01-15T00:00:00Z",
            profile_id="prof123",
            category="education",
            sensitivity="normal",
            thumbnail_url="https://example.com/thumb.jpg",
            is_verified=True,
            is_subscribed=False,
            live_stream_enabled=True
        )
        
        assert channel.id == "ch123"
        assert channel.name == "Test Channel"
        assert channel.video_count == 150
        assert channel.subscriber_count == "5.2K"
        assert channel.is_verified == True
        assert channel.live_stream_enabled == True
    
    def test_channel_post_init(self):
        """Test Channel post-initialization"""
        channel = Channel(id="ch123")
        
        # Should auto-generate channel URL
        assert channel.channel_url == "https://www.bitchute.com/channel/ch123/"
        
        # Should have timestamp
        assert channel.scrape_timestamp > 0
    
    def test_channel_subscriber_count_numeric(self):
        """Test subscriber count conversion"""
        # K suffix
        channel1 = Channel(id="ch1", subscriber_count="5.2K")
        assert channel1.subscriber_count_numeric == 5200
        
        # M suffix
        channel2 = Channel(id="ch2", subscriber_count="1.5M")
        assert channel2.subscriber_count_numeric == 1500000
        
        # Plain number
        channel3 = Channel(id="ch3", subscriber_count="500")
        assert channel3.subscriber_count_numeric == 500
        
        # Empty/invalid
        channel4 = Channel(id="ch4", subscriber_count="")
        assert channel4.subscriber_count_numeric == 0
        
        channel5 = Channel(id="ch5", subscriber_count="invalid")
        assert channel5.subscriber_count_numeric == 0
    
    def test_channel_average_views_per_video(self):
        """Test average views calculation"""
        # Normal case
        channel = Channel(
            id="ch123",
            video_count=50,
            view_count=100000
        )
        assert channel.average_views_per_video == 2000.0
        
        # No videos
        channel_no_videos = Channel(id="ch456", video_count=0, view_count=1000)
        assert channel_no_videos.average_views_per_video == 0.0
    
    def test_channel_to_dict(self):
        """Test channel conversion to dictionary"""
        channel = Channel(
            id="ch123",
            name="Test Channel",
            video_count=50,
            subscriber_count="1.2K",
            view_count=60000
        )
        
        data = channel.to_dict()
        
        assert isinstance(data, dict)
        assert data['id'] == "ch123"
        assert data['name'] == "Test Channel"
        assert data['subscriber_count_numeric'] == 1200
        assert data['average_views_per_video'] == 1200.0


class TestHashtagModel:
    """Test Hashtag data model"""
    
    def test_hashtag_initialization(self):
        """Test Hashtag initialization"""
        hashtag = Hashtag(
            name="test",
            rank=1,
            video_count=500
        )
        
        assert hashtag.name == "test"
        assert hashtag.rank == 1
        assert hashtag.video_count == 500
        assert hashtag.scrape_timestamp > 0
    
    def test_hashtag_post_init(self):
        """Test Hashtag post-initialization"""
        hashtag = Hashtag(name="test")
        
        # Should auto-generate URL
        assert hashtag.url == "https://www.bitchute.com/hashtag/test/"
    
    def test_hashtag_name_formatting(self):
        """Test hashtag name formatting"""
        # Without # prefix
        hashtag1 = Hashtag(name="test")
        assert hashtag1.clean_name == "test"
        assert hashtag1.formatted_name == "#test"
        
        # With # prefix
        hashtag2 = Hashtag(name="#test")
        assert hashtag2.clean_name == "test"
        assert hashtag2.formatted_name == "#test"
        
        # Empty name
        hashtag3 = Hashtag(name="")
        assert hashtag3.clean_name == ""
        assert hashtag3.formatted_name == ""
    
    def test_hashtag_to_dict(self):
        """Test hashtag conversion to dictionary"""
        hashtag = Hashtag(name="test", rank=1, video_count=100)
        
        data = hashtag.to_dict()
        
        assert data['name'] == "test"
        assert data['clean_name'] == "test"
        assert data['formatted_name'] == "#test"
        assert data['rank'] == 1
        assert data['video_count'] == 100
        assert 'scrape_timestamp' in data


class TestSearchResult:
    """Test SearchResult model"""
    
    def test_search_result_initialization(self):
        """Test SearchResult initialization"""
        result = SearchResult(
            query="test query",
            total_results=100,
            results_per_page=50,
            current_page=1
        )
        
        assert result.query == "test query"
        assert result.total_results == 100
        assert result.results_per_page == 50
        assert result.current_page == 1
        assert result.search_timestamp > 0
    
    def test_search_result_properties(self):
        """Test SearchResult properties"""
        # With results
        video1 = Video(id="v1", title="Video 1")
        video2 = Video(id="v2", title="Video 2")
        channel1 = Channel(id="ch1", name="Channel 1")
        
        result = SearchResult(
            query="test",
            videos=[video1, video2],
            channels=[channel1]
        )
        
        assert result.has_results == True
        assert result.video_count == 2
        assert result.channel_count == 1
        
        # Empty results
        empty_result = SearchResult(query="test")
        assert empty_result.has_results == False
        assert empty_result.video_count == 0
        assert empty_result.channel_count == 0


class TestAPIStats:
    """Test APIStats model"""
    
    def test_api_stats_initialization(self):
        """Test APIStats initialization"""
        stats = APIStats()
        
        assert stats.requests_made == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0
        assert stats.cache_hits == 0
        assert stats.session_start_time > 0
    
    def test_api_stats_rates(self):
        """Test APIStats rate calculations"""
        stats = APIStats(
            requests_made=100,
            successful_requests=90,
            failed_requests=10,
            cache_hits=20
        )
        
        assert stats.success_rate == 0.9
        assert stats.error_rate == 0.1
        assert stats.cache_hit_rate == 20/120  # cache_hits / (requests + cache_hits)
        
        # No requests
        empty_stats = APIStats()
        assert empty_stats.success_rate == 0.0
        assert empty_stats.error_rate == 0.0
        assert empty_stats.cache_hit_rate == 0.0
    
    def test_api_stats_session_duration(self):
        """Test session duration calculation"""
        import time
        
        stats = APIStats()
        time.sleep(0.1)  # Small delay
        
        duration = stats.session_duration
        assert duration > 0
        assert duration < 1  # Should be less than 1 second
        
        # With last request time
        stats.last_request_time = stats.session_start_time + 60
        assert stats.session_duration == 60
    
    def test_api_stats_to_dict(self):
        """Test APIStats conversion to dictionary"""
        stats = APIStats(
            requests_made=50,
            successful_requests=45,
            failed_requests=5,
            total_videos_scraped=100
        )
        
        data = stats.to_dict()
        
        assert data['requests_made'] == 50
        assert data['success_rate'] == 0.9
        assert data['error_rate'] == 0.1
        assert data['total_videos_scraped'] == 100
        assert 'session_duration' in data


class TestModelRelationships:
    """Test relationships between models"""
    
    def test_video_channel_relationship(self):
        """Test Video-Channel relationship"""
        channel = Channel(id="ch123", name="Test Channel")
        video = Video(
            id="v123",
            title="Test Video",
            channel_id=channel.id,
            channel_name=channel.name
        )
        
        assert video.channel_id == channel.id
        assert video.channel_name == channel.name
    
    def test_video_hashtag_relationship(self):
        """Test Video-Hashtag relationship"""
        hashtag1 = Hashtag(name="test1")
        hashtag2 = Hashtag(name="test2")
        
        video = Video(
            id="v123",
            title="Test Video",
            hashtags=[hashtag1.formatted_name, hashtag2.formatted_name]
        )
        
        assert len(video.hashtags) == 2
        assert "#test1" in video.hashtags
        assert "#test2" in video.hashtags
    
    def test_search_result_aggregation(self):
        """Test SearchResult aggregating videos and channels"""
        videos = [
            Video(id=f"v{i}", title=f"Video {i}")
            for i in range(5)
        ]
        
        channels = [
            Channel(id=f"ch{i}", name=f"Channel {i}")
            for i in range(3)
        ]
        
        result = SearchResult(
            query="test",
            total_results=8,
            videos=videos,
            channels=channels
        )
        
        assert result.video_count == 5
        assert result.channel_count == 3
        assert len(result.videos) == 5
        assert len(result.channels) == 3