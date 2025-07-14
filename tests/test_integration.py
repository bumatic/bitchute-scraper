"""
Integration tests for BitChute API scraper
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
import tempfile
from pathlib import Path

from bitchute.core import BitChuteAPI
from bitchute.utils import DataExporter
from bitchute.exceptions import BitChuteAPIError, ValidationError


class TestFullWorkflow:
    """Test complete workflows"""
    
    @patch('bitchute.core.TokenManager')
    @patch('requests.Session.post')
    def test_complete_trending_workflow(self, mock_post, mock_token_manager):
        """Test complete workflow from API creation to data export"""
        # Mock token manager
        mock_token_manager.return_value.get_token.return_value = "mock_token"
        mock_token_manager.return_value.has_valid_token.return_value = True
        mock_token_manager.return_value.cleanup.return_value = None
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'videos': [
                {
                    'id': 'workflow1',
                    'title': 'Workflow Test Video',
                    'view_count': 1000,
                    'duration': '5:30',
                    'uploader': {'id': 'wch1', 'name': 'Workflow Channel'},
                    'hashtags': ['workflow', 'test']
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Test complete workflow
        with BitChuteAPI(verbose=False) as api:
            # Get trending videos
            df = api.get_trending_videos('day', limit=10)
            
            # Verify data
            assert len(df) == 1
            assert df.iloc[0]['id'] == 'workflow1'
            assert df.iloc[0]['title'] == 'Workflow Test Video'
            
            # Export data
            with tempfile.TemporaryDirectory() as temp_dir:
                filename = str(Path(temp_dir) / "workflow_test")
                exporter = DataExporter()
                exported = exporter.export_data(df, filename, ['csv', 'json'])
                
                assert 'csv' in exported
                assert 'json' in exported
                assert Path(exported['csv']).exists()
                assert Path(exported['json']).exists()
            
            # Check API stats
            stats = api.get_api_stats()
            assert stats['requests_made'] > 0
            assert isinstance(stats['error_rate'], float)
    
    @patch('bitchute.core.TokenManager')
    def test_error_handling_workflow(self, mock_token_manager):
        """Test error handling in complete workflow"""
        # Mock token manager
        mock_token_manager.return_value.get_token.return_value = "mock_token"
        mock_token_manager.return_value.has_valid_token.return_value = True
        mock_token_manager.return_value.cleanup.return_value = None
        
        with BitChuteAPI(verbose=False) as api:
            # Test validation errors
            with pytest.raises(ValidationError):
                api.get_trending_videos('invalid_timeframe')
            
            with pytest.raises(ValidationError):
                api.search_videos('')  # Empty query
            
            with pytest.raises(ValidationError):
                api.get_video_details('')  # Empty video ID


class TestDataExportIntegration:
    """Test data export integration"""
    
    def test_export_multiple_formats(self, sample_dataframe):
        """Test exporting data to multiple formats"""
        exporter = DataExporter()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filename = str(Path(temp_dir) / "integration_test")
            
            exported = exporter.export_data(
                sample_dataframe,
                filename,
                ['csv', 'json']
            )
            
            # Verify files were created
            assert 'csv' in exported
            assert 'json' in exported
            
            csv_file = Path(exported['csv'])
            json_file = Path(exported['json'])
            
            assert csv_file.exists()
            assert json_file.exists()
            
            # Verify file contents
            df_from_csv = pd.read_csv(csv_file)
            assert len(df_from_csv) == len(sample_dataframe)
            assert set(df_from_csv.columns) == set(sample_dataframe.columns)
