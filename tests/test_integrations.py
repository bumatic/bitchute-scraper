"""
Integration tests for BitChute scraper
"""

import pytest
import pandas as pd
from unittest.mock import patch, Mock
import time
from pathlib import Path
import tempfile

from bitchute import BitChuteAPI, SortOrder, SensitivityLevel
from bitchute.utils import DataExporter, DataAnalyzer, ContentFilter
from bitchute.exceptions import BitChuteAPIError, ValidationError


@pytest.mark.integration
class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""
    
    @pytest.fixture
    def mock_api_responses(self):
        """Create comprehensive mock API responses"""
        return {
            "trending_videos": {
                "videos": [
                    {
                        "video_id": f"trend{i}",
                        "video_name": f"Trending Video {i}",
                        "view_count": 1000 * (i + 1),
                        "duration": f"{i+5}:30",
                        "date_published": f"2024-01-{i+1:02d}",
                        "channel": {
                            "channel_id": f"ch{i % 3}",
                            "channel_name": f"Channel {i % 3}"
                        },
                        "hashtags": [
                            {"hashtag_id": "trending", "hashtag_count": 100},
                            {"hashtag_id": f"tag{i}", "hashtag_count": 50}
                        ],
                        "category_id": "news" if i % 2 == 0 else "education"
                    }
                    for i in range(10)
                ]
            },
            "video_counts": {
                "like_count": 100,
                "dislike_count": 10,
                "view_count": 1500
            },
            "search_results": {
                "videos": [
                    {
                        "video_id": f"search{i}",
                        "video_name": f"Search Result {i}",
                        "view_count": 500 * (i + 1),
                        "channel": {"channel_id": f"ch{i}", "channel_name": f"Channel {i}"}
                    }
                    for i in range(5)
                ]
            },
            "channels": {
                "channels": [
                    {
                        "channel_id": f"ch{i}",
                        "channel_name": f"Channel {i}",
                        "video_count": 50 + i * 10,
                        "subscriber_count": f"{i+1}K"
                    }
                    for i in range(3)
                ]
            },
            "hashtags": {
                "hashtags": [
                    {"hashtag_id": f"tag{i}", "hashtag_count": 1000 - i * 100}
                    for i in range(5)
                ]
            }
        }
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_complete_data_collection_workflow(self, mock_request, mock_api_responses):
        """Test complete workflow: collect, analyze, filter, export"""
        # Setup mock responses
        mock_request.side_effect = [
            mock_api_responses["trending_videos"],
            mock_api_responses["search_results"],
            mock_api_responses["channels"],
            mock_api_responses["hashtags"]
        ]
        
        api = BitChuteAPI(verbose=True)
        
        # Step 1: Collect data from multiple sources
        trending = api.get_trending_videos('day', limit=10)
        search_results = api.search_videos('test query', limit=5)
        channels = api.search_channels('channel', limit=3)
        hashtags = api.get_trending_hashtags(limit=5)
        
        # Verify data collection
        assert len(trending) == 10
        assert len(search_results) == 5
        assert len(channels) == 3
        assert len(hashtags) == 5
        
        # Step 2: Analyze trending videos
        analyzer = DataAnalyzer()
        analysis = analyzer.analyze_videos(trending)
        
        assert analysis['total_videos'] == 10
        assert analysis['views']['total'] == sum(1000 * (i + 1) for i in range(10))
        assert 'top_channels' in analysis
        assert 'categories' in analysis
        
        # Step 3: Filter videos
        content_filter = ContentFilter()
        
        # Filter by views
        high_view_videos = content_filter.filter_by_views(trending, min_views=5000)
        assert len(high_view_videos) >= 5
        
        # Filter by category
        news_videos = content_filter.filter_by_keywords(trending, ['news'], column='category_id')
        assert all(v == 'news' for v in news_videos['category_id'])
        
        # Step 4: Export data
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = DataExporter()
            
            # Export to multiple formats
            exported = exporter.export_data(
                trending,
                str(Path(tmpdir) / "trending"),
                formats=['csv', 'json']
            )
            
            assert 'csv' in exported
            assert 'json' in exported
            assert Path(exported['csv']).exists()
            assert Path(exported['json']).exists()
            
            # Verify exported data
            df_from_csv = pd.read_csv(exported['csv'])
            assert len(df_from_csv) == 10
            assert list(df_from_csv.columns) == list(trending.columns)
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_video_enrichment_workflow(self, mock_request, mock_api_responses):
        """Test workflow with video detail enrichment"""
        # First call returns basic video list
        basic_videos = mock_api_responses["trending_videos"].copy()
        
        # Subsequent calls return video details
        mock_request.side_effect = [
            basic_videos,  # Initial trending request
            # Then detail requests for each video
            *[mock_api_responses["video_counts"] for _ in range(10)]
        ]
        
        api = BitChuteAPI(verbose=False)
        
        # Get videos with details
        videos = api.get_trending_videos('week', limit=10, include_details=True)
        
        # Verify enrichment
        assert len(videos) == 10
        assert all(videos['like_count'] == 100)
        assert all(videos['dislike_count'] == 10)
        
        # Calculate engagement metrics
        for _, video in videos.iterrows():
            if 'view_count' in video and video['view_count'] > 0:
                engagement_rate = (video['like_count'] + video['dislike_count']) / video['view_count']
                assert engagement_rate > 0
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_pagination_workflow(self, mock_request, mock_api_responses):
        """Test pagination across multiple API calls"""
        # Create paginated responses
        all_videos = []
        for page in range(3):
            videos = [
                {
                    "video_id": f"page{page}_video{i}",
                    "video_name": f"Page {page} Video {i}",
                    "view_count": 100,
                    "channel": {"channel_id": "ch1", "channel_name": "Channel 1"}
                }
                for i in range(50)
            ]
            all_videos.extend(videos)
        
        # Mock paginated responses
        mock_request.side_effect = [
            {"videos": all_videos[0:50]},    # Page 1
            {"videos": all_videos[50:100]},  # Page 2
            {"videos": all_videos[100:150]}, # Page 3
            {"videos": []}                    # Empty page (end)
        ]
        
        api = BitChuteAPI(verbose=False)
        
        # Get 150 videos across 3 pages
        with patch('time.sleep'):  # Skip rate limiting in test
            videos = api.get_recent_videos(limit=150, per_page=50)
        
        assert len(videos) == 150
        assert videos.iloc[0]['id'] == 'page0_video0'
        assert videos.iloc[149]['id'] == 'page2_video49'
        
        # Verify pagination calls
        assert mock_request.call_count == 4  # 3 pages + 1 empty
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_error_recovery_workflow(self, mock_request):
        """Test workflow with error recovery"""
        # Mock mixed success/failure responses
        mock_request.side_effect = [
            {"videos": [{"video_id": "v1", "video_name": "Video 1"}]},  # Success
            Exception("Network error"),                                   # Failure
            {"videos": [{"video_id": "v2", "video_name": "Video 2"}]},  # Success after retry
        ]
        
        api = BitChuteAPI(verbose=True, max_retries=2)
        
        # First call succeeds
        videos1 = api.get_trending_videos('day', limit=1)
        assert len(videos1) == 1
        
        # Second call fails but should not crash
        with pytest.raises(BitChuteAPIError):
            api.get_trending_videos('week', limit=1)
        
        # Third call should still work
        videos2 = api.get_trending_videos('month', limit=1)
        assert len(videos2) == 1
        
        # Check statistics
        stats = api.get_api_stats()
        assert stats['requests_made'] >= 2
        assert stats['errors'] >= 1


@pytest.mark.integration
class TestDataPipeline:
    """Test data processing pipeline"""
    
    def test_video_data_pipeline(self):
        """Test complete video data processing pipeline"""
        # Create sample data
        raw_data = [
            {
                "video_id": f"vid{i}",
                "video_name": f"Video Title {i}",
                "description": f"Description for video {i}",
                "view_count": 1000 * (i + 1),
                "duration": f"{5 + i}:30",
                "channel": {
                    "channel_id": f"ch{i % 3}",
                    "channel_name": f"Channel {i % 3}"
                },
                "hashtags": [
                    {"hashtag_id": "common", "hashtag_count": 100},
                    {"hashtag_id": f"unique{i}", "hashtag_count": 50}
                ]
            }
            for i in range(20)
        ]
        
        # Process through pipeline
        from bitchute.utils import DataProcessor
        processor = DataProcessor()
        
        # Parse videos
        videos = [processor.parse_video(data, i+1) for i, data in enumerate(raw_data)]
        
        # Convert to DataFrame
        df = pd.DataFrame([v.__dict__ for v in videos])
        
        # Apply filters
        filter_obj = ContentFilter()
        
        # Filter by views
        popular = filter_obj.filter_by_views(df, min_views=10000)
        assert len(popular) == 11  # Videos with 10k+ views
        
        # Filter by duration
        short_videos = filter_obj.filter_by_duration(df, max_seconds=600)  # Under 10 min
        assert len(short_videos) == 5  # First 5 videos are under 10 min
        
        # Analyze filtered data
        analyzer = DataAnalyzer()
        analysis = analyzer.analyze_videos(popular)
        
        assert analysis['total_videos'] == 11
        assert analysis['views']['min'] >= 10000
        
        # Export pipeline results
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = DataExporter()
            
            # Export different subsets
            exports = {
                'all_videos': df,
                'popular_videos': popular,
                'short_videos': short_videos
            }
            
            for name, data in exports.items():
                exported = exporter.export_data(
                    data,
                    str(Path(tmpdir) / name),
                    ['csv']
                )
                assert Path(exported['csv']).exists()
    
    def test_channel_aggregation_pipeline(self):
        """Test channel data aggregation pipeline"""
        # Create video data with channels
        video_data = []
        channels_info = {
            'ch0': {'name': 'Tech Channel', 'videos': 8},
            'ch1': {'name': 'News Channel', 'videos': 7},
            'ch2': {'name': 'Education Channel', 'videos': 5}
        }
        
        video_id = 0
        for ch_id, info in channels_info.items():
            for _ in range(info['videos']):
                video_data.append({
                    'id': f'v{video_id}',
                    'title': f'Video {video_id}',
                    'channel_id': ch_id,
                    'channel_name': info['name'],
                    'view_count': 1000 + video_id * 100,
                    'duration': '5:00'
                })
                video_id += 1
        
        df = pd.DataFrame(video_data)
        
        # Aggregate by channel
        channel_stats = df.groupby(['channel_id', 'channel_name']).agg({
            'id': 'count',
            'view_count': ['sum', 'mean']
        }).reset_index()
        
        # Flatten column names
        channel_stats.columns = ['channel_id', 'channel_name', 'video_count', 'total_views', 'avg_views']
        
        # Verify aggregation
        assert len(channel_stats) == 3
        assert channel_stats.iloc[0]['video_count'] == 8  # Tech Channel
        assert channel_stats.iloc[1]['video_count'] == 7  # News Channel
        assert channel_stats.iloc[2]['video_count'] == 5  # Education Channel


@pytest.mark.integration
class TestConcurrentOperations:
    """Test concurrent API operations"""
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_concurrent_search_operations(self, mock_request):
        """Test multiple concurrent searches"""
        import concurrent.futures
        
        # Mock responses for different queries
        def create_search_response(query):
            return {
                "videos": [
                    {
                        "video_id": f"{query}_result{i}",
                        "video_name": f"{query} Result {i}",
                        "view_count": 100 * i,
                        "channel": {"channel_id": "ch1", "channel_name": "Channel 1"}
                    }
                    for i in range(5)
                ]
            }
        
        # Configure mock to return different results based on query
        def mock_response(endpoint, payload):
            query = payload.get('query', '')
            return create_search_response(query)
        
        mock_request.side_effect = mock_response
        
        api = BitChuteAPI(verbose=False)
        queries = ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'defi']
        
        # Run searches concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_query = {
                executor.submit(api.search_videos, query, limit=5): query
                for query in queries
            }
            
            results = {}
            for future in concurrent.futures.as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    df = future.result()
                    results[query] = df
                except Exception as e:
                    results[query] = f"Error: {e}"
        
        # Verify all searches completed
        assert len(results) == 5
        for query in queries:
            assert query in results
            assert isinstance(results[query], pd.DataFrame)
            assert len(results[query]) == 5
            # Verify query-specific results
            assert all(query in v for v in results[query]['id'])


@pytest.mark.integration
class TestRealAPIBehavior:
    """Test behavior that mimics real API responses"""
    
    @pytest.mark.slow
    @patch('requests.Session.post')
    def test_realistic_api_delays(self, mock_post):
        """Test with realistic API response times"""
        import random
        
        def delayed_response(*args, **kwargs):
            # Simulate variable API response time
            delay = random.uniform(0.1, 0.3)
            time.sleep(delay)
            
            response = Mock()
            response.status_code = 200
            response.json.return_value = {
                "videos": [{"video_id": "test", "video_name": "Test"}]
            }
            return response
        
        mock_post.side_effect = delayed_response
        
        api = BitChuteAPI(verbose=True, rate_limit=0.5)
        
        # Make multiple requests
        start_time = time.time()
        for i in range(3):
            api.get_trending_videos('day', limit=1)
        
        total_time = time.time() - start_time
        
        # Should take at least 1 second due to rate limiting (2 * 0.5s)
        assert total_time >= 1.0
        
        # But not too long (accounting for API delays)
        assert total_time < 2.5
    
    @patch.object(BitChuteAPI, '_make_request')
    def test_api_response_variations(self, mock_request):
        """Test handling of various API response formats"""
        # Different response structures that might occur
        responses = [
            # Normal response
            {"videos": [{"video_id": "v1", "video_name": "Normal"}]},
            
            # Response with extra fields
            {
                "videos": [{"video_id": "v2", "video_name": "Extra", "extra_field": "value"}],
                "metadata": {"total": 100}
            },
            
            # Response with missing optional fields
            {"videos": [{"video_id": "v3"}]},  # No video_name
            
            # Empty but valid response
            {"videos": []},
        ]
        
        mock_request.side_effect = responses
        
        api = BitChuteAPI(verbose=True)
        
        # Test each response type
        for i in range(4):
            try:
                df = api.get_trending_videos('day', limit=1)
                if i < 3:
                    assert len(df) == 1
                else:
                    assert len(df) == 0  # Empty response
            except Exception as e:
                pytest.fail(f"Failed on response {i}: {e}") 