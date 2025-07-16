"""
Test utility functions
"""

import pytest
import pandas as pd
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import os

from bitchute.utils import (
    RateLimiter, RequestBuilder, DataProcessor, PaginationHelper,
    BulkProcessor, DataExporter, DataAnalyzer, ContentFilter, CacheManager
)
from bitchute.models import Video, Channel, Hashtag


class TestRateLimiter:
    """Test RateLimiter functionality"""
    
    def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization"""
        limiter = RateLimiter(0.5)
        assert limiter.rate_limit == 0.5
        assert limiter.last_request == 0
    
    def test_rate_limiter_wait(self):
        """Test rate limiting enforcement"""
        limiter = RateLimiter(0.1)  # 100ms limit
        
        start = time.time()
        limiter.wait()
        first_wait = time.time() - start
        
        # First wait should be immediate
        assert first_wait < 0.05
        
        # Second wait should enforce rate limit
        start = time.time()
        limiter.wait()
        second_wait = time.time() - start
        
        assert second_wait >= 0.08  # Allow small margin
    
    def test_rate_limiter_thread_safety(self):
        """Test thread safety of rate limiter"""
        import threading
        
        limiter = RateLimiter(0.1)
        wait_times = []
        
        def wait_and_record():
            start = time.time()
            limiter.wait()
            wait_times.append(time.time() - start)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=wait_and_record)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # At least some threads should have waited
        assert any(t > 0.08 for t in wait_times)


class TestRequestBuilder:
    """Test RequestBuilder functionality"""
    
    def test_build_video_request(self):
        """Test video request building"""
        # Basic request
        request = RequestBuilder.build_video_request("trending-day", limit=20)
        assert request == {
            "selection": "trending-day",
            "offset": 0,
            "limit": 20,
            "advertisable": True
        }
        
        # With optional parameters
        request = RequestBuilder.build_video_request(
            "all",
            offset=50,
            limit=30,
            advertisable=False,
            is_short=True
        )
        assert request["offset"] == 50
        assert request["advertisable"] == False
        assert request["is_short"] == True
    
    def test_build_search_request(self):
        """Test search request building"""
        # Basic search
        request = RequestBuilder.build_search_request("bitcoin")
        assert request == {
            "offset": 0,
            "limit": 50,
            "query": "bitcoin",
            "sensitivity_id": "normal"
        }
        
        # With all parameters
        request = RequestBuilder.build_search_request(
            "test query",
            offset=100,
            limit=25,
            sensitivity="nsfw",
            sort="views"
        )
        assert request["offset"] == 100
        assert request["limit"] == 25
        assert request["sensitivity_id"] == "nsfw"
        assert request["sort"] == "views"
    
    def test_build_hashtag_request(self):
        """Test hashtag request building"""
        request = RequestBuilder.build_hashtag_request()
        assert request == {"offset": 0, "limit": 50}
        
        request = RequestBuilder.build_hashtag_request(offset=20, limit=30)
        assert request["offset"] == 20
        assert request["limit"] == 30
    
    def test_build_video_detail_request(self):
        """Test video detail request building"""
        request = RequestBuilder.build_video_detail_request("test123")
        assert request == {"video_id": "test123"}


class TestDataProcessor:
    """Test DataProcessor functionality"""
    
    @pytest.fixture
    def processor(self):
        return DataProcessor()
    
    def test_parse_video_basic(self, processor):
        """Test basic video parsing"""
        data = {
            "video_id": "test123",
            "video_name": "Test Video",
            "description": "Description",
            "view_count": "1500",
            "duration": "10:30",
            "date_published": "2024-01-15",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "category_id": "news",
            "sensitivity_id": "normal",
            "state_id": "published"
        }
        
        video = processor.parse_video(data)
        
        assert isinstance(video, Video)
        assert video.id == "test123"
        assert video.title == "Test Video"
        assert video.view_count == 1500
        assert video.duration == "10:30"
        assert video.category == "news"
    
    def test_parse_video_with_channel(self, processor):
        """Test video parsing with channel data"""
        data = {
            "video_id": "test123",
            "video_name": "Test Video",
            "channel": {
                "channel_id": "ch123",
                "channel_name": "Test Channel"
            }
        }
        
        video = processor.parse_video(data)
        assert video.channel_id == "ch123"
        assert video.channel_name == "Test Channel"
    
    def test_parse_video_with_hashtags(self, processor):
        """Test video parsing with hashtags"""
        # New format
        data = {
            "video_id": "test123",
            "video_name": "Test",
            "hashtags": [
                {"hashtag_id": "bitcoin", "hashtag_count": 100},
                {"hashtag_id": "crypto", "hashtag_count": 50}
            ]
        }
        
        video = processor.parse_video(data)
        assert len(video.hashtags) == 2
        assert "#bitcoin" in video.hashtags
        assert "#crypto" in video.hashtags
        
        # Old format
        data["hashtags"] = ["test", "example"]
        video = processor.parse_video(data)
        assert "#test" in video.hashtags
        assert "#example" in video.hashtags
    
    def test_parse_video_edge_cases(self, processor):
        """Test video parsing edge cases"""
        # Missing fields
        data = {"video_id": "test123"}
        video = processor.parse_video(data)
        assert video.id == "test123"
        assert video.title == ""
        assert video.view_count == 0
        
        # Invalid view count
        data = {"video_id": "test123", "view_count": "invalid"}
        video = processor.parse_video(data)
        assert video.view_count == 0
        
        # None values
        data = {"video_id": "test123", "video_name": None}
        video = processor.parse_video(data)
        assert video.title == ""
    
    def test_parse_channel(self, processor):
        """Test channel parsing"""
        data = {
            "channel_id": "ch123",
            "channel_name": "Test Channel",
            "description": "Channel description",
            "video_count": "150",
            "subscriber_count": "5.2K",
            "view_count": 250000,
            "date_created": "2022-01-01",
            "profile_id": "prof123"
        }
        
        channel = processor.parse_channel(data)
        
        assert isinstance(channel, Channel)
        assert channel.id == "ch123"
        assert channel.name == "Test Channel"
        assert channel.video_count == 150
        assert channel.subscriber_count == "5.2K"
        assert channel.view_count == 250000
    
    def test_parse_hashtag(self, processor):
        """Test hashtag parsing"""
        # New format
        data = {"hashtag_id": "bitcoin", "hashtag_count": 500}
        hashtag = processor.parse_hashtag(data, rank=1)
        
        assert isinstance(hashtag, Hashtag)
        assert hashtag.name == "bitcoin"
        assert hashtag.video_count == 500
        assert hashtag.rank == 1
        
        # Old format
        data = {"name": "crypto", "video_count": 300}
        hashtag = processor.parse_hashtag(data, rank=2)
        assert hashtag.name == "crypto"
        assert hashtag.video_count == 300
    
    def test_safe_get(self, processor):
        """Test safe value retrieval"""
        data = {"key": "value", "number": 123, "none": None}
        
        assert processor._safe_get(data, "key") == "value"
        assert processor._safe_get(data, "number") == "123"
        assert processor._safe_get(data, "none", "default") == "default"
        assert processor._safe_get(data, "missing", "default") == "default"
    
    def test_safe_int(self, processor):
        """Test safe integer conversion"""
        assert processor._safe_int(123) == 123
        assert processor._safe_int("456") == 456
        assert processor._safe_int("789.5") == 789
        assert processor._safe_int("invalid") == 0
        assert processor._safe_int(None) == 0
        assert processor._safe_int("") == 0


class TestDataExporter:
    """Test DataExporter functionality"""
    
    @pytest.fixture
    def exporter(self):
        return DataExporter()
    
    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            'id': ['v1', 'v2', 'v3'],
            'title': ['Video 1', 'Video 2', 'Video 3'],
            'view_count': [1000, 2000, 3000]
        })
    
    def test_export_csv(self, exporter, sample_df, tmp_path):
        """Test CSV export"""
        os.chdir(tmp_path)
        exported = exporter.export_data(sample_df, "test", ["csv"])
        
        assert "csv" in exported
        assert Path(exported["csv"]).exists()
        
        # Verify content
        df_loaded = pd.read_csv(exported["csv"])
        assert len(df_loaded) == 3
        assert list(df_loaded.columns) == ['id', 'title', 'view_count']
    
    def test_export_json(self, exporter, sample_df, tmp_path):
        """Test JSON export"""
        os.chdir(tmp_path)
        exported = exporter.export_data(sample_df, "test", ["json"])
        
        assert "json" in exported
        assert Path(exported["json"]).exists()
        
        # Verify content
        with open(exported["json"], 'r') as f:
            data = json.load(f)
        assert len(data) == 3
        assert data[0]["id"] == "v1"
    
    def test_export_excel(self, exporter, sample_df, tmp_path):
        """Test Excel export"""
        os.chdir(tmp_path)
        exported = exporter.export_data(sample_df, "test", ["xlsx"])
        
        assert "xlsx" in exported
        assert Path(exported["xlsx"]).exists()
        
        # Verify content
        df_loaded = pd.read_excel(exported["xlsx"])
        assert len(df_loaded) == 3
    
    def test_export_parquet(self, exporter, sample_df, tmp_path):
        """Test Parquet export"""
        os.chdir(tmp_path)
        exported = exporter.export_data(sample_df, "test", ["parquet"])
        
        assert "parquet" in exported
        assert Path(exported["parquet"]).exists()
        
        # Verify content
        df_loaded = pd.read_parquet(exported["parquet"])
        assert len(df_loaded) == 3
    
    def test_export_multiple_formats(self, exporter, sample_df, tmp_path):
        """Test exporting to multiple formats"""
        os.chdir(tmp_path)
        exported = exporter.export_data(sample_df, "test", ["csv", "json"])
        
        assert len(exported) == 2
        assert "csv" in exported
        assert "json" in exported
        assert Path(exported["csv"]).exists()
        assert Path(exported["json"]).exists()
    
    def test_export_with_timestamp(self, exporter, sample_df, tmp_path):
        """Test that exports include timestamp"""
        os.chdir(tmp_path)
        exported = exporter.export_data(sample_df, "test", ["csv"])
        
        filename = Path(exported["csv"]).name
        # Should have format: test_YYYYMMDD_HHMMSS.csv
        assert filename.startswith("test_")
        assert filename.count("_") >= 2
        assert filename.endswith(".csv")
    
    def test_export_invalid_format(self, exporter, sample_df, tmp_path):
        """Test handling of invalid format"""
        os.chdir(tmp_path)
        exported = exporter.export_data(sample_df, "test", ["invalid"])
        
        # Should skip invalid format
        assert "invalid" not in exported
        assert len(exported) == 0


class TestDataAnalyzer:
    """Test DataAnalyzer functionality"""
    
    @pytest.fixture
    def analyzer(self):
        return DataAnalyzer()
    
    @pytest.fixture
    def video_df(self):
        return pd.DataFrame({
            'id': ['v1', 'v2', 'v3', 'v4', 'v5'],
            'title': ['Video 1', 'Video 2', 'Video 3', 'Video 4', 'Video 5'],
            'view_count': [1000, 2000, 3000, 4000, 5000],
            'channel_name': ['Ch A', 'Ch B', 'Ch A', 'Ch C', 'Ch A'],
            'duration': ['5:30', '10:15', '3:45', '15:00', '7:20'],
            'category': ['news', 'news', 'education', 'news', 'education'],
            'hashtags': [
                ['#bitcoin', '#crypto'],
                ['#news'],
                ['#bitcoin', '#education'],
                ['#politics', '#news'],
                ['#crypto', '#defi']
            ]
        })
    
    def test_analyze_videos_basic(self, analyzer, video_df):
        """Test basic video analysis"""
        analysis = analyzer.analyze_videos(video_df)
        
        assert analysis['total_videos'] == 5
        assert 'timestamp' in analysis
        
        # View statistics
        assert analysis['views']['total'] == 15000
        assert analysis['views']['average'] == 3000
        assert analysis['views']['median'] == 3000
        assert analysis['views']['max'] == 5000
        assert analysis['views']['min'] == 1000
    
    def test_analyze_channels(self, analyzer, video_df):
        """Test channel analysis"""
        analysis = analyzer.analyze_videos(video_df)
        
        assert 'top_channels' in analysis
        assert 'unique_channels' in analysis
        assert analysis['unique_channels'] == 3
        
        # Ch A should be top with 3 videos
        top_channels = analysis['top_channels']
        assert list(top_channels.keys())[0] == 'Ch A'
        assert top_channels['Ch A'] == 3
    
    def test_analyze_categories(self, analyzer, video_df):
        """Test category analysis"""
        analysis = analyzer.analyze_videos(video_df)
        
        assert 'categories' in analysis
        categories = analysis['categories']
        assert categories['news'] == 3
        assert categories['education'] == 2
    
    def test_analyze_duration(self, analyzer, video_df):
        """Test duration analysis"""
        analysis = analyzer.analyze_videos(video_df)
        
        assert 'duration' in analysis
        duration = analysis['duration']
        assert 'average_seconds' in duration
        assert 'average_minutes' in duration
        assert duration['average_minutes'] > 0
    
    def test_analyze_hashtags(self, analyzer, video_df):
        """Test hashtag analysis"""
        analysis = analyzer.analyze_videos(video_df)
        
        assert 'top_hashtags' in analysis
        hashtags = analysis['top_hashtags']
        
        # Bitcoin and crypto should be top
        assert '#bitcoin' in hashtags
        assert '#crypto' in hashtags
        assert hashtags['#bitcoin'] == 2
        assert hashtags['#crypto'] == 2
    
    def test_analyze_empty_dataframe(self, analyzer):
        """Test analysis of empty DataFrame"""
        empty_df = pd.DataFrame()
        analysis = analyzer.analyze_videos(empty_df)
        
        assert analysis == {'error': 'No data to analyze'}
    
    def test_parse_duration(self, analyzer):
        """Test duration parsing"""
        assert analyzer._parse_duration("5:30") == 330
        assert analyzer._parse_duration("1:23:45") == 5025
        assert analyzer._parse_duration("invalid") == 0
        assert analyzer._parse_duration("") == 0
        assert analyzer._parse_duration(None) == 0


class TestContentFilter:
    """Test ContentFilter functionality"""
    
    @pytest.fixture
    def filter_obj(self):
        return ContentFilter()
    
    @pytest.fixture
    def video_df(self):
        return pd.DataFrame({
            'id': ['v1', 'v2', 'v3', 'v4', 'v5'],
            'title': ['Bitcoin News', 'Crypto Update', 'Politics Today', 'Bitcoin Analysis', 'Random Video'],
            'view_count': [500, 1500, 2500, 3500, 4500],
            'channel_name': ['Crypto Ch', 'Crypto Ch', 'News Ch', 'Finance Ch', 'Random Ch'],
            'duration': ['2:30', '5:45', '15:20', '10:00', '30:15'],
            'upload_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05']
        })
    
    def test_filter_by_views(self, filter_obj, video_df):
        """Test filtering by view count"""
        # Min views
        filtered = filter_obj.filter_by_views(video_df, min_views=2000)
        assert len(filtered) == 3
        assert all(filtered['view_count'] >= 2000)
        
        # Min and max views
        filtered = filter_obj.filter_by_views(video_df, min_views=1000, max_views=3000)
        assert len(filtered) == 2
        assert all((filtered['view_count'] >= 1000) & (filtered['view_count'] <= 3000))
    
    def test_filter_by_duration(self, filter_obj, video_df):
        """Test filtering by duration"""
        # Min duration (5 minutes)
        filtered = filter_obj.filter_by_duration(video_df, min_seconds=300)
        assert len(filtered) == 4  # All except the 2:30 video
        
        # Max duration (20 minutes)
        filtered = filter_obj.filter_by_duration(video_df, max_seconds=1200)
        assert len(filtered) == 4  # All except the 30:15 video
    
    def test_filter_by_keywords(self, filter_obj, video_df):
        """Test filtering by keywords"""
        # Single keyword
        filtered = filter_obj.filter_by_keywords(video_df, ['bitcoin'])
        assert len(filtered) == 2
        assert all('Bitcoin' in title for title in filtered['title'])
        
        # Multiple keywords
        filtered = filter_obj.filter_by_keywords(video_df, ['bitcoin', 'crypto'])
        assert len(filtered) == 3
        
        # Case insensitive
        filtered = filter_obj.filter_by_keywords(video_df, ['BITCOIN'])
        assert len(filtered) == 2
    
    def test_filter_by_channel(self, filter_obj, video_df):
        """Test filtering by channel"""
        filtered = filter_obj.filter_by_channel(video_df, ['Crypto Ch'])
        assert len(filtered) == 2
        assert all(filtered['channel_name'] == 'Crypto Ch')
        
        # Multiple channels
        filtered = filter_obj.filter_by_channel(video_df, ['Crypto Ch', 'News Ch'])
        assert len(filtered) == 3
    
    def test_filter_by_date_range(self, filter_obj, video_df):
        """Test filtering by date range"""
        # After start date
        filtered = filter_obj.filter_by_date_range(video_df, start_date='2024-01-03')
        assert len(filtered) == 3
        
        # Before end date
        filtered = filter_obj.filter_by_date_range(video_df, end_date='2024-01-03')
        assert len(filtered) == 3
        
        # Between dates
        filtered = filter_obj.filter_by_date_range(
            video_df,
            start_date='2024-01-02',
            end_date='2024-01-04'
        )
        assert len(filtered) == 3
    
    def test_filter_empty_dataframe(self, filter_obj):
        """Test filtering empty DataFrame"""
        empty_df = pd.DataFrame()
        
        filtered = filter_obj.filter_by_views(empty_df, min_views=1000)
        assert len(filtered) == 0
        
        filtered = filter_obj.filter_by_keywords(empty_df, ['test'])
        assert len(filtered) == 0


class TestCacheManager:
    """Test CacheManager functionality"""
    
    def test_cache_initialization(self):
        """Test cache initialization"""
        cache = CacheManager(max_size=100, ttl=300)
        assert cache.max_size == 100
        assert cache.ttl == 300
        assert cache.size() == 0
    
    def test_cache_set_and_get(self):
        """Test cache set and get operations"""
        cache = CacheManager()
        
        # Set value
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.size() == 1
        
        # Set another value
        cache.set("key2", {"data": "value2"})
        assert cache.get("key2") == {"data": "value2"}
        assert cache.size() == 2
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration"""
        cache = CacheManager(ttl=0.1)  # 100ms TTL
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.15)
        assert cache.get("key1") is None
        assert cache.size() == 0
    
    def test_cache_max_size(self):
        """Test cache size limit"""
        cache = CacheManager(max_size=3)
        
        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        assert cache.size() == 3
        
        # Add one more - should evict oldest
        cache.set("key4", "value4")
        assert cache.size() == 3
        assert cache.get("key1") is None  # Oldest was evicted
        assert cache.get("key4") == "value4"
    
    def test_cache_clear(self):
        """Test cache clearing"""
        cache = CacheManager()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2
        
        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cache_thread_safety(self):
        """Test thread safety of cache"""
        import threading
        
        cache = CacheManager()
        results = []
        
        def set_and_get(key, value):
            cache.set(key, value)
            time.sleep(0.01)  # Small delay
            result = cache.get(key)
            results.append(result == value)
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=set_and_get, args=(f"key{i}", f"value{i}"))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All operations should succeed
        assert all(results)
        assert cache.size() == 10


class TestPaginationHelper:
    """Test PaginationHelper functionality"""
    
    @pytest.fixture
    def mock_api_method(self):
        """Create mock API method that returns paginated data"""
        def method(limit=50, offset=0, **kwargs):
            # Simulate API with 150 total items
            all_items = [{"id": f"item{i}", "value": i} for i in range(150)]
            
            # Return requested page
            start = offset
            end = min(offset + limit, len(all_items))
            items = all_items[start:end]
            
            return pd.DataFrame(items) if items else pd.DataFrame()
        
        return method
    
    def test_get_multiple_pages(self, mock_api_method):
        """Test getting multiple pages"""
        with patch('time.sleep'):  # Skip delays in tests
            result = PaginationHelper.get_multiple_pages(
                mock_api_method,
                max_pages=3,
                per_page=50
            )
        
        assert len(result) == 150  # All items
        assert result.iloc[0]['id'] == 'item0'
        assert result.iloc[149]['id'] == 'item149'
    
    def test_pagination_with_partial_last_page(self, mock_api_method):
        """Test pagination when last page is partial"""
        with patch('time.sleep'):
            result = PaginationHelper.get_multiple_pages(
                mock_api_method,
                max_pages=4,
                per_page=40  # 150 items = 4 pages (40, 40, 40, 30)
            )
        
        assert len(result) == 150
    
    def test_pagination_stops_on_empty_page(self, mock_api_method):
        """Test pagination stops when empty page is returned"""
        def method_with_early_stop(limit=50, offset=0, **kwargs):
            # Return items up to index 75 only
            all_items = [{"id": f"item{i}", "value": i} for i in range(75)]
            
            start = offset
            end = min(offset + limit, len(all_items))
            
            if start >= len(all_items):
                return pd.DataFrame()
            
            items = all_items[start:end]
            return pd.DataFrame(items) if items else pd.DataFrame()
        
        with patch('time.sleep'):
            result = PaginationHelper.get_multiple_pages(
                method_with_early_stop,
                max_pages=5,
                per_page=50
            )
        
        assert len(result) == 75  # Should stop at 75, not try for 250
    
    def test_pagination_with_extra_kwargs(self, mock_api_method):
        """Test pagination passes through extra kwargs"""
        called_with_kwargs = []
        
        def method_tracking_kwargs(**kwargs):
            called_with_kwargs.append(kwargs)
            return mock_api_method(**kwargs)
        
        with patch('time.sleep'):
            PaginationHelper.get_multiple_pages(
                method_tracking_kwargs,
                max_pages=2,
                per_page=50,
                extra_param="test_value"
            )
        
        # Check that extra_param was passed through
        assert all(kwargs.get('extra_param') == 'test_value' for kwargs in called_with_kwargs)


class TestBulkProcessor:
    """Test BulkProcessor functionality"""
    
    @pytest.fixture
    def mock_api_client(self):
        """Create mock API client"""
        client = Mock()
        
        def get_video_details(video_id, **kwargs):
            video = Video(
                id=video_id,
                title=f"Video {video_id}",
                view_count=1000,
                like_count=100 if kwargs.get('include_counts') else 0,
                media_url="http://example.com/video.mp4" if kwargs.get('include_media') else ""
            )
            return video
        
        client.get_video_details = Mock(side_effect=get_video_details)
        return client
    
    def test_process_video_details(self, mock_api_client):
        """Test bulk video details processing"""
        video_ids = [f"video{i}" for i in range(5)]
        
        videos = BulkProcessor.process_video_details(
            mock_api_client,
            video_ids,
            max_workers=3,
            include_counts=True
        )
        
        assert len(videos) == 5
        assert all(isinstance(v, Video) for v in videos)
        assert all(v.like_count == 100 for v in videos)
        assert mock_api_client.get_video_details.call_count == 5
    
    def test_process_with_failures(self, mock_api_client):
        """Test bulk processing with some failures"""
        def get_video_with_errors(video_id, **kwargs):
            if video_id == "video2":
                raise Exception("API Error")
            return Video(id=video_id, title=f"Video {video_id}")
        
        mock_api_client.get_video_details = Mock(side_effect=get_video_with_errors)
        
        video_ids = [f"video{i}" for i in range(5)]
        videos = BulkProcessor.process_video_details(mock_api_client, video_ids)
        
        # Should get 4 videos (one failed)
        assert len(videos) == 4
        assert not any(v.id == "video2" for v in videos)
    
    def test_process_empty_list(self, mock_api_client):
        """Test processing empty list"""
        videos = BulkProcessor.process_video_details(mock_api_client, [])
        assert videos == []
        mock_api_client.get_video_details.assert_not_called()


class TestRequestBuilderEdgeCases:
    """Test edge cases for RequestBuilder"""
    
    def test_build_requests_with_none_values(self):
        """Test request building with None values"""
        # Should not include None values in request
        request = RequestBuilder.build_video_request(
            "all",
            is_short=None  # Should be omitted
        )
        assert "is_short" not in request
        
        request = RequestBuilder.build_search_request(
            "query",
            sort=None  # Should be omitted
        )
        assert "sort" not in request


class TestDataProcessorErrorHandling:
    """Test DataProcessor error handling"""
    
    @pytest.fixture
    def processor(self):
        return DataProcessor()
    
    def test_parse_video_with_exception(self, processor):
        """Test video parsing when exception occurs"""
        # This should not raise exception, just log warning
        data = {
            "video_id": "test123",
            "video_name": "Test",
            "view_count": Mock(side_effect=Exception("Parse error"))
        }
        
        video = processor.parse_video(data)
        assert video.id == "test123"
        assert video.view_count == 0  # Default value
    
    def test_parse_malformed_data(self, processor):
        """Test parsing with malformed data"""
        # Completely wrong structure
        data = "not a dict"
        video = processor.parse_video({})  # Empty dict
        assert isinstance(video, Video)
        assert video.id == ""
        
        # Nested errors
        data = {
            "video_id": "test",
            "channel": "not a dict"  # Should be dict
        }
        video = processor.parse_video(data)
        assert video.id == "test"
        assert video.channel_id == ""