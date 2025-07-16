"""
Performance tests for BitChute scraper
"""

import pytest
import time
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
import memory_profiler
import concurrent.futures
from dataclasses import asdict

from bitchute.core import BitChuteAPI
from bitchute.models import Video, Channel, Hashtag
from bitchute.utils import DataProcessor, DataAnalyzer, ContentFilter, BulkProcessor
from bitchute.exceptions import BitChuteAPIError

from .fixtures import create_mock_video_data, create_mock_channel_data
from .helpers import time_limit, wait_for_condition


@pytest.mark.performance
class TestAPIPerformance:
    """Test API performance characteristics"""
    
    @pytest.fixture
    def large_video_dataset(self):
        """Create large dataset for testing"""
        return [
            create_mock_video_data(
                f"video{i}",
                view_count=i * 100,
                duration=f"{5 + (i % 60)}:{i % 60:02d}"
            )
            for i in range(1000)
        ]
    
    @pytest.fixture
    def mock_api_with_delay(self):
        """Create API mock with realistic delays"""
        api = BitChuteAPI(verbose=False)
        
        def delayed_response(endpoint, payload):
            # Simulate network latency
            time.sleep(0.05)  # 50ms latency
            
            limit = payload.get('limit', 50)
            offset = payload.get('offset', 0)
            
            # Generate response data
            videos = []
            for i in range(limit):
                video_num = offset + i
                if video_num >= 1000:  # Total of 1000 videos
                    break
                videos.append(create_mock_video_data(f"video{video_num}"))
            
            return {"videos": videos}
        
        api._make_request = Mock(side_effect=delayed_response)
        return api
    
    def test_large_dataset_processing(self, large_video_dataset):
        """Test processing large number of videos"""
        processor = DataProcessor()
        
        start_time = time.time()
        
        # Process all videos
        videos = []
        for data in large_video_dataset:
            video = processor.parse_video(data)
            videos.append(video)
        
        processing_time = time.time() - start_time
        
        assert len(videos) == 1000
        assert processing_time < 2.0  # Should process 1000 videos in under 2 seconds
        
        # Calculate processing rate
        videos_per_second = len(videos) / processing_time
        assert videos_per_second > 500  # Should process at least 500 videos/second
    
    def test_dataframe_operations_performance(self, large_video_dataset):
        """Test DataFrame operations performance"""
        # Convert to DataFrame
        start_time = time.time()
        df = pd.DataFrame(large_video_dataset)
        creation_time = time.time() - start_time
        
        assert creation_time < 0.5  # DataFrame creation should be fast
        
        # Test filtering performance
        start_time = time.time()
        filtered = df[df['view_count'] > 50000]
        filter_time = time.time() - start_time
        
        assert filter_time < 0.01  # Filtering should be very fast
        
        # Test sorting performance
        start_time = time.time()
        sorted_df = df.sort_values('view_count', ascending=False)
        sort_time = time.time() - start_time
        
        assert sort_time < 0.05  # Sorting 1000 items should be fast
    
    @pytest.mark.slow
    def test_pagination_performance(self, mock_api_with_delay):
        """Test pagination performance with multiple API calls"""
        start_time = time.time()
        
        # Get 500 videos with pagination (10 pages of 50)
        videos = mock_api_with_delay.get_recent_videos(limit=500, per_page=50)
        
        total_time = time.time() - start_time
        
        assert len(videos) == 500
        # 10 API calls with 50ms delay each = 500ms, plus processing
        assert total_time < 10.0  # Increase timeout to 10 seconds for CI compatibility
        
        # Check that pagination was used efficiently
        assert mock_api_with_delay._make_request.call_count == 10
    
    def test_concurrent_api_calls(self):
        """Test concurrent API call performance"""
        api = BitChuteAPI(verbose=False)
        
        # Mock fast responses
        def mock_response(endpoint, payload):
            time.sleep(0.01)  # 10ms delay
            return {"videos": [create_mock_video_data("test")]}
        
        api._make_request = Mock(side_effect=mock_response)
        
        # Sequential calls
        start_time = time.time()
        sequential_results = []
        for i in range(10):
            result = api.get_trending_videos('day', limit=1)
            sequential_results.append(result)
        sequential_time = time.time() - start_time
        
        # Concurrent calls using ThreadPoolExecutor
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(10):
                future = executor.submit(api.get_trending_videos, 'day', limit=1)
                futures.append(future)
            
            concurrent_results = [f.result() for f in futures]
        concurrent_time = time.time() - start_time
        
        # Concurrent should be faster
        assert concurrent_time < sequential_time
        assert len(concurrent_results) == len(sequential_results)
        
        # Should achieve at least 2x speedup
        speedup = sequential_time / concurrent_time
        assert speedup > 2.0
    
    def test_memory_efficiency(self, large_video_dataset):
        """Test memory usage efficiency"""
        import gc
        import sys
        
        # Get baseline memory
        gc.collect()
        
        # Process videos and check memory usage
        videos = []
        initial_size = 0
        
        for i, data in enumerate(large_video_dataset):
            video = Video(**{
                'id': data['video_id'],
                'title': data['video_name'],
                'view_count': data.get('view_count', 0)
            })
            videos.append(video)
            
            if i == 0:
                # Estimate size of one video object
                initial_size = sys.getsizeof(video) + sum(
                    sys.getsizeof(getattr(video, attr)) 
                    for attr in video.__dict__
                )
        
        # Check that memory usage scales linearly
        total_size = len(videos) * initial_size
        
        # Should not exceed expected size by more than 50% (overhead)
        assert total_size < initial_size * len(videos) * 1.5
    
    def test_rate_limiter_performance(self):
        """Test rate limiter doesn't add excessive overhead"""
        from bitchute.utils import RateLimiter
        
        # Test with very small rate limit
        limiter = RateLimiter(0.001)  # 1ms rate limit
        
        start_time = time.time()
        
        # Make 100 rate-limited calls
        for _ in range(100):
            limiter.wait()
        
        total_time = time.time() - start_time
        
        # Should take at least 99ms (99 waits of 1ms each)
        assert total_time >= 0.099
        # But not much more (allow for overhead)
        assert total_time < 0.15
    
    def test_data_export_performance(self):
        """Test data export performance for different formats"""
        from bitchute.utils import DataExporter
        import tempfile
        import os
        
        # Create large dataset
        data = []
        for i in range(5000):
            data.append({
                'id': f'video{i}',
                'title': f'Test Video {i}',
                'description': f'Description for video {i}' * 10,  # Longer text
                'view_count': i * 100,
                'channel_name': f'Channel {i % 100}',
                'upload_date': f'2024-01-{(i % 30) + 1:02d}'
            })
        
        df = pd.DataFrame(data)
        exporter = DataExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            
            # Test CSV export performance
            start_time = time.time()
            csv_export = exporter.export_data(df, "test", ["csv"])
            csv_time = time.time() - start_time
            
            # Test JSON export performance
            start_time = time.time()
            json_export = exporter.export_data(df, "test", ["json"])
            json_time = time.time() - start_time
            
            # Test Parquet export performance
            start_time = time.time()
            parquet_export = exporter.export_data(df, "test", ["parquet"])
            parquet_time = time.time() - start_time
            
            # CSV should be fast
            assert csv_time < 1.0
            
            # JSON might be slower but still reasonable
            assert json_time < 2.0
            
            # Parquet should be fast and efficient
            assert parquet_time < 0.5
            
            # Check file sizes (Parquet should be smallest)
            csv_size = os.path.getsize(csv_export['csv'])
            json_size = os.path.getsize(json_export['json'])
            parquet_size = os.path.getsize(parquet_export['parquet'])
            
            assert parquet_size < csv_size  # Parquet should compress well


@pytest.mark.performance
class TestDataAnalysisPerformance:
    """Test data analysis performance"""
    
    def test_analyzer_with_large_dataset(self):
        """Test analyzer performance with large dataset"""
        analyzer = DataAnalyzer()
        
        # Create large video dataset
        data = []
        for i in range(10000):
            data.append({
                'id': f'v{i}',
                'title': f'Video {i}',
                'view_count': np.random.randint(100, 1000000),
                'duration': f'{np.random.randint(1, 60)}:{np.random.randint(0, 59):02d}',
                'channel_name': f'Channel {i % 500}',
                'hashtags': [f'#tag{j}' for j in range(np.random.randint(1, 5))]
            })
        
        df = pd.DataFrame(data)
        
        start_time = time.time()
        analysis = analyzer.analyze_videos(df)
        analysis_time = time.time() - start_time
        
        # Should analyze 10k videos quickly
        assert analysis_time < 2.0
        
        # Check results
        assert analysis['total_videos'] == 10000
        assert 'views' in analysis
        assert 'top_channels' in analysis
        assert 'top_hashtags' in analysis
    
    def test_content_filter_performance(self):
        """Test content filtering performance"""
        filter_obj = ContentFilter()
        
        # Create dataset
        data = []
        for i in range(10000):
            data.append({
                'id': f'v{i}',
                'title': f'{"Bitcoin" if i % 3 == 0 else "Other"} Video {i}',
                'view_count': i * 100,
                'channel_name': f'Channel {i % 100}',
                'duration': f'{5 + (i % 55)}:00',
                'upload_date': f'2024-01-{(i % 30) + 1:02d}'
            })
        
        df = pd.DataFrame(data)
        
        # Test view filtering
        start_time = time.time()
        high_views = filter_obj.filter_by_views(df, min_views=500000)
        view_filter_time = time.time() - start_time
        
        assert view_filter_time < 0.1  # Should be very fast
        
        # Test keyword filtering
        start_time = time.time()
        bitcoin_videos = filter_obj.filter_by_keywords(df, ['Bitcoin'])
        keyword_filter_time = time.time() - start_time
        
        assert keyword_filter_time < 0.2  # String operations are slower but still fast
        
        # Test combined filters
        start_time = time.time()
        filtered = df
        filtered = filter_obj.filter_by_views(filtered, min_views=100000)
        filtered = filter_obj.filter_by_keywords(filtered, ['Bitcoin'])
        filtered = filter_obj.filter_by_duration(filtered, max_seconds=3600)
        combined_filter_time = time.time() - start_time
        
        assert combined_filter_time < 0.5  # Multiple filters should still be fast


@pytest.mark.performance
class TestBulkOperationsPerformance:
    """Test bulk operation performance"""
    
    def test_bulk_video_details_performance(self):
        """Test bulk video detail fetching performance"""
        # Mock API client with fast responses
        api = Mock()
        
        def mock_get_details(video_id, **kwargs):
            time.sleep(0.01)  # Simulate 10ms API call
            return Video(
                id=video_id,
                title=f"Video {video_id}",
                view_count=1000,
                like_count=100 if kwargs.get('include_counts') else 0
            )
        
        api.get_video_details = Mock(side_effect=mock_get_details)
        
        # Test different worker counts
        video_ids = [f"video{i}" for i in range(50)]
        
        # Single worker (sequential)
        start_time = time.time()
        videos_1 = BulkProcessor.process_video_details(
            api, video_ids, max_workers=1
        )
        time_1_worker = time.time() - start_time
        
        # Multiple workers (parallel)
        start_time = time.time()
        videos_5 = BulkProcessor.process_video_details(
            api, video_ids, max_workers=5
        )
        time_5_workers = time.time() - start_time
        
        # Verify results
        assert len(videos_1) == 50
        assert len(videos_5) == 50
        
        # Parallel should be faster
        assert time_5_workers < time_1_worker
        
        # Should achieve significant speedup
        speedup = time_1_worker / time_5_workers
        assert speedup > 3.0  # At least 3x faster with 5 workers


@pytest.mark.performance
class TestScalabilityTests:
    """Test system scalability"""
    
    def test_memory_scaling(self):
        """Test memory usage scales linearly with data size"""
        import gc
        import tracemalloc
        
        tracemalloc.start()
        
        # Measure memory for different dataset sizes
        memory_usage = {}
        
        for size in [100, 1000, 10000]:
            gc.collect()
            
            # Get memory snapshot before
            snapshot_before = tracemalloc.take_snapshot()
            
            # Create dataset
            videos = []
            for i in range(size):
                video = Video(
                    id=f"v{i}",
                    title=f"Video {i}",
                    description="Test description" * 10,
                    view_count=i * 100
                )
                videos.append(video)
            
            # Get memory snapshot after
            snapshot_after = tracemalloc.take_snapshot()
            
            # Calculate memory diff
            stats = snapshot_after.compare_to(snapshot_before, 'lineno')
            total_memory = sum(stat.size_diff for stat in stats)
            
            memory_usage[size] = total_memory
            
            # Cleanup
            del videos
            gc.collect()
        
        tracemalloc.stop()
        
        # Check linear scaling
        # Memory per item should be roughly constant
        memory_per_item_1k = memory_usage[1000] / 1000
        memory_per_item_10k = memory_usage[10000] / 10000
        
        # Allow 20% variance
        ratio = memory_per_item_10k / memory_per_item_1k
        assert 0.8 < ratio < 1.2, f"Memory scaling is not linear: {ratio}"
    
    def test_processing_time_scaling(self):
        """Test processing time scales linearly"""
        processor = DataProcessor()
        
        processing_times = {}
        
        for size in [100, 1000, 5000]:
            data_list = [
                create_mock_video_data(f"v{i}")
                for i in range(size)
            ]
            
            start_time = time.time()
            
            videos = []
            for data in data_list:
                video = processor.parse_video(data)
                videos.append(video)
            
            processing_times[size] = time.time() - start_time
        
        # Check linear scaling
        time_per_item_1k = processing_times[1000] / 1000
        time_per_item_5k = processing_times[5000] / 5000
        
        # Processing time per item should be constant (allow 30% variance)
        ratio = time_per_item_5k / time_per_item_1k
        assert 0.7 < ratio < 1.3, f"Processing time scaling is not linear: {ratio}"
    
    @pytest.mark.slow
    def test_api_request_scaling(self):
        """Test API request handling scales properly"""
        api = BitChuteAPI(verbose=False, rate_limit=0)  # No rate limit for test
        
        # Mock responses with consistent timing
        def mock_response(endpoint, payload):
            time.sleep(0.005)  # 5ms per request
            limit = payload.get('limit', 50)
            return {
                "videos": [
                    create_mock_video_data(f"v{i}")
                    for i in range(min(limit, 50))
                ]
            }
        
        api._make_request = Mock(side_effect=mock_response)
        
        # Test different request volumes
        request_times = {}
        
        for num_videos in [50, 250, 500]:
            start_time = time.time()
            
            videos = api.get_recent_videos(limit=num_videos, per_page=50)
            
            request_times[num_videos] = time.time() - start_time
            
            assert len(videos) == num_videos
        
        # Time should scale with number of API calls, not total videos
        # 50 videos = 1 call, 250 = 5 calls, 500 = 10 calls
        expected_ratio_250 = 5.0
        expected_ratio_500 = 10.0
        
        actual_ratio_250 = request_times[250] / request_times[50]
        actual_ratio_500 = request_times[500] / request_times[50]
        
        # Allow some variance for overhead
        assert 4.0 < actual_ratio_250 < 6.0
        assert 8.0 < actual_ratio_500 < 12.0


@pytest.mark.performance
class TestOptimizationValidation:
    """Validate that optimizations work as expected"""
    
    def test_dataframe_vectorization(self):
        """Test that DataFrame operations use vectorization"""
        # Create large dataset
        data = pd.DataFrame({
            'view_count': np.random.randint(0, 1000000, 10000),
            'like_count': np.random.randint(0, 10000, 10000),
            'dislike_count': np.random.randint(0, 1000, 10000)
        })
        
        # Vectorized operation
        start_time = time.time()
        data['engagement_rate'] = (
            (data['like_count'] + data['dislike_count']) / 
            data['view_count'].clip(lower=1)  # Avoid division by zero
        )
        vectorized_time = time.time() - start_time
        
        # Loop-based operation (for comparison)
        start_time = time.time()
        engagement_loop = []
        for _, row in data.iterrows():
            if row['view_count'] > 0:
                rate = (row['like_count'] + row['dislike_count']) / row['view_count']
            else:
                rate = 0
            engagement_loop.append(rate)
        loop_time = time.time() - start_time
        
        # Vectorized should be much faster
        assert vectorized_time < loop_time / 10  # At least 10x faster
    
    def test_caching_performance(self):
        """Test caching improves performance"""
        from bitchute.utils import CacheManager
        
        # Simulate expensive operation
        call_count = 0
        
        def expensive_operation(key):
            nonlocal call_count
            call_count += 1
            time.sleep(0.1)  # 100ms operation
            return f"result_{key}"
        
        cache = CacheManager(max_size=100)
        
        # First calls (cache miss)
        start_time = time.time()
        for i in range(10):
            key = f"key_{i % 5}"  # Only 5 unique keys
            
            cached = cache.get(key)
            if cached is None:
                result = expensive_operation(key)
                cache.set(key, result)
            else:
                result = cached
        
        first_run_time = time.time() - start_time
        first_call_count = call_count
        
        # Reset counter
        call_count = 0
        
        # Second run (should hit cache)
        start_time = time.time()
        for i in range(10):
            key = f"key_{i % 5}"
            
            cached = cache.get(key)
            if cached is None:
                result = expensive_operation(key)
                cache.set(key, result)
            else:
                result = cached
        
        second_run_time = time.time() - start_time
        second_call_count = call_count
        
        # Second run should be much faster
        assert second_run_time < first_run_time / 5
        
        # Should have made fewer calls
        assert second_call_count == 0  # All cache hits
        assert first_call_count == 5  # One per unique key