"""
Tests for utility functions
"""

import pytest
import pandas as pd
import time
import threading
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path

from bitchute.utils import (
    RateLimiter, DataProcessor, DataExporter, DataAnalyzer
)
from bitchute.models import Video, Channel, Hashtag


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    def test_rate_limiter_basic(self):
        """Test basic rate limiting"""
        limiter = RateLimiter(0.1)  # 100ms between requests
        
        start_time = time.time()
        limiter.wait()
        limiter.wait()
        end_time = time.time()
        
        # Should take at least 100ms
        assert end_time - start_time >= 0.09  # Small tolerance for timing


class TestDataProcessor:
    """Test data processing functions"""
    
    def setup_method(self):
        self.processor = DataProcessor()
    
    def test_parse_video_basic(self, mock_video_data):
        """Test basic video parsing"""
        video = self.processor.parse_video(mock_video_data)
        
        assert video.id == 'test123'
        assert video.title == 'Test Video'
        assert video.view_count == 1000
        assert video.channel_id == 'channel123'
        assert video.channel_name == 'Test Channel'
        assert video.hashtags == ['#test', '#video', '#example']
        assert video.video_url == 'https://www.bitchute.com/video/test123/'
    
    def test_parse_video_missing_fields(self):
        """Test video parsing with missing fields"""
        data = {'id': 'test123'}
        video = self.processor.parse_video(data)
        
        assert video.id == 'test123'
        assert video.title == ''
        assert video.view_count == 0
        assert video.hashtags == []
    
    def test_safe_int_conversion(self):
        """Test safe integer conversion"""
        assert self.processor._safe_int(100) == 100
        assert self.processor._safe_int('100') == 100
        assert self.processor._safe_int('100.5') == 100
        assert self.processor._safe_int(None) == 0
        assert self.processor._safe_int('invalid') == 0


class TestDataExporter:
    """Test data export functionality"""
    
    def test_export_csv(self, sample_dataframe):
        """Test CSV export"""
        exporter = DataExporter()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            filename = str(temp_path / "test")
            
            exported = exporter.export_data(sample_dataframe, filename, ['csv'])
            
            assert 'csv' in exported
            csv_file = Path(exported['csv'])
            assert csv_file.exists()
            
            # Verify content
            df_loaded = pd.read_csv(csv_file)
            assert len(df_loaded) == len(sample_dataframe)
            assert 'id' in df_loaded.columns


class TestDataAnalyzer:
    """Test data analysis functionality"""
    
    def test_analyze_videos_basic(self, sample_dataframe):
        """Test basic video analysis"""
        analyzer = DataAnalyzer()
        analysis = analyzer.analyze_videos(sample_dataframe)
        
        assert analysis['total_videos'] == 2
        assert 'views' in analysis
        assert analysis['views']['total'] == 3000  # 1000 + 2000
        assert analysis['views']['average'] == 1500
