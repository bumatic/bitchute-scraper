"""
Tests for BitChute CLI functionality.

Tests all CLI commands, argument parsing, output formatting, and error handling.
Uses mocked API responses and temporary directories for fast, isolated testing.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from io import StringIO
import sys

from bitchute.cli import main, create_argument_parser, CLIDataManager, CLIResultPrinter
from bitchute.core import BitChuteAPI
from bitchute.exceptions import BitChuteAPIError, ValidationError


@pytest.fixture
def mock_api():
    """Create a mock BitChute API instance with sample data."""
    api = Mock(spec=BitChuteAPI)
    
    # Sample video data with ALL required fields
    sample_videos = pd.DataFrame([
        {
            'id': 'video123',
            'title': 'Sample Video 1',
            'view_count': 1500,
            'like_count': 50,
            'dislike_count': 5,
            'channel_name': 'Test Channel',
            'duration': '12:34',
            'upload_date': '2024-01-15'
        },
        {
            'id': 'video456', 
            'title': 'Sample Video 2',
            'view_count': 2300,
            'like_count': 75,
            'dislike_count': 8,
            'channel_name': 'News Channel',
            'duration': '8:45',
            'upload_date': '2024-01-16'
        }
    ])
    
    # Sample channel data with ALL required fields
    sample_channels = pd.DataFrame([
        {
            'id': 'channel123',
            'name': 'Test Channel',
            'video_count': 50,
            'subscriber_count': '1.2K',
            'view_count': 75000,
            'created_date': '2024-01-01'
        }
    ])
    
    # Sample hashtag data
    sample_hashtags = pd.DataFrame([
        {'name': 'bitcoin', 'rank': 1},
        {'name': 'crypto', 'rank': 2}
    ])
    
    # Configure mock methods
    api.get_trending_videos.return_value = sample_videos
    api.get_popular_videos.return_value = sample_videos
    api.get_recent_videos.return_value = sample_videos
    api.search_videos.return_value = sample_videos
    api.search_channels.return_value = sample_channels
    api.get_trending_hashtags.return_value = sample_hashtags
    api.get_video_info.return_value = sample_videos.iloc[:1]
    api.get_channel_info.return_value = sample_channels.iloc[:1]
    api.get_channel_videos.return_value = sample_videos
    
    return api


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary directory for output files."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


class TestCLICommandExecution:
    """Test execution of all CLI commands with valid arguments."""
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_trending_command_basic_execution(self, mock_api_class, mock_api, temp_output_dir, monkeypatch):
        """Test basic trending command execution."""
        mock_api_class.return_value = mock_api
        monkeypatch.chdir(temp_output_dir)
        
        # Test trending command without format argument (it's global)
        test_args = ['trending', '--timeframe', 'day', '--limit', '10']
        
        with patch('sys.argv', ['bitchute'] + test_args):
            with patch('bitchute.cli.CLIDataManager.save_data'):
                result = main()
        
        assert result == 0
        mock_api.get_trending_videos.assert_called_once_with(
            timeframe='day', 
            limit=10, 
            include_details=True
        )
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_popular_command_with_analysis(self, mock_api_class, mock_api, temp_output_dir, monkeypatch):
        """Test popular command with analysis flag."""
        mock_api_class.return_value = mock_api
        monkeypatch.chdir(temp_output_dir)
        
        # Global arguments come before subcommand
        test_args = ['--analyze', 'popular', '--limit', '50']
        
        with patch('sys.argv', ['bitchute'] + test_args):
            with patch('bitchute.cli.CLIDataManager.save_data'):
                result = main()
        
        assert result == 0
        mock_api.get_popular_videos.assert_called_once_with(
            limit=50, 
            include_details=True
        )
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_search_command_with_filters(self, mock_api_class, mock_api, temp_output_dir, monkeypatch):
        """Test search command with sorting and sensitivity filters."""
        mock_api_class.return_value = mock_api
        monkeypatch.chdir(temp_output_dir)
        
        test_args = [
            'search', 'bitcoin', 
            '--limit', '25', 
            '--sort', 'views', 
            '--sensitivity', 'normal'
        ]
        
        with patch('sys.argv', ['bitchute'] + test_args):
            with patch('bitchute.cli.CLIDataManager.save_data'):
                result = main()
        
        assert result == 0
        mock_api.search_videos.assert_called_once_with(
            query='bitcoin',
            limit=25,
            sensitivity='normal',
            sort='views',
            include_details=True
        )
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_channels_search_command(self, mock_api_class, mock_api, temp_output_dir, monkeypatch):
        """Test channel search command."""
        mock_api_class.return_value = mock_api
        monkeypatch.chdir(temp_output_dir)
        
        test_args = ['channels', 'news', '--limit', '20', '--sensitivity', 'normal']
        
        with patch('sys.argv', ['bitchute'] + test_args):
            with patch('bitchute.cli.CLIDataManager.save_data'):
                result = main()
        
        assert result == 0
        mock_api.search_channels.assert_called_once_with(
            query='news',
            limit=20,
            sensitivity='normal',
            include_details=True
        )
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_hashtags_command(self, mock_api_class, mock_api, temp_output_dir, monkeypatch):
        """Test hashtags command execution."""
        mock_api_class.return_value = mock_api
        monkeypatch.chdir(temp_output_dir)
        
        test_args = ['hashtags', '--limit', '30']
        
        with patch('sys.argv', ['bitchute'] + test_args):
            with patch('bitchute.cli.CLIDataManager.save_data'):
                result = main()
        
        assert result == 0
        mock_api.get_trending_hashtags.assert_called_once_with(limit=30)
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_video_command_with_details(self, mock_api_class, mock_api, temp_output_dir, monkeypatch):
        """Test individual video command with counts and media."""
        mock_api_class.return_value = mock_api
        monkeypatch.chdir(temp_output_dir)
        
        test_args = ['video', 'CLrgZP4RWyly', '--counts', '--media']
        
        with patch('sys.argv', ['bitchute'] + test_args):
            with patch('bitchute.cli.CLIDataManager.save_data'):
                result = main()
        
        assert result == 0
        mock_api.get_video_info.assert_called_once_with(
            video_id='CLrgZP4RWyly',
            include_counts=True,
            include_media=True
        )
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_channel_command(self, mock_api_class, mock_api, temp_output_dir, monkeypatch):
        """Test individual channel command."""
        mock_api_class.return_value = mock_api
        monkeypatch.chdir(temp_output_dir)
        
        test_args = ['channel', 'test_channel_123']
        
        with patch('sys.argv', ['bitchute'] + test_args):
            with patch('bitchute.cli.CLIDataManager.save_data'):
                result = main()
        
        assert result == 0
        mock_api.get_channel_info.assert_called_once_with(channel_id='test_channel_123')
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_channel_videos_command(self, mock_api_class, mock_api, temp_output_dir, monkeypatch):
        """Test channel videos command with ordering."""
        mock_api_class.return_value = mock_api
        monkeypatch.chdir(temp_output_dir)
        
        test_args = [
            'channel-videos', 'test_channel_123', 
            '--limit', '50', 
            '--order', 'popular'
        ]
        
        with patch('sys.argv', ['bitchute'] + test_args):
            with patch('bitchute.cli.CLIDataManager.save_data'):
                result = main()
        
        assert result == 0
        mock_api.get_channel_videos.assert_called_once_with(
            channel_id='test_channel_123',
            limit=50,
            order_by='popular',
            include_details=True
        )


class TestCLIArgumentParsing:
    """Test CLI argument parsing and validation."""
    
    def test_argument_parser_creation(self):
        """Test argument parser is created correctly."""
        parser = create_argument_parser()
        assert parser is not None
        assert parser.description is not None
    
    def test_valid_argument_combinations(self):
        """Test valid argument combinations are parsed correctly."""
        parser = create_argument_parser()
        
        # Test trending with global arguments in correct position
        args = parser.parse_args([
            '--verbose', '--format', 'csv,json', '--analyze',
            'trending', '--timeframe', 'week', '--limit', '100'
        ])
        assert args.command == 'trending'
        assert args.timeframe == 'week'
        assert args.limit == 100
        assert args.format == 'csv,json'
        assert args.analyze is True
        assert args.verbose is True
    
    def test_search_argument_parsing(self):
        """Test search command argument parsing."""
        parser = create_argument_parser()
        
        args = parser.parse_args([
            'search', 'climate change', '--limit', '50', 
            '--sort', 'views', '--sensitivity', 'nsfw'
        ])
        assert args.command == 'search'
        assert args.query == 'climate change'
        assert args.limit == 50
        assert args.sort == 'views'
        assert args.sensitivity == 'nsfw'
    
    def test_default_values_application(self):
        """Test default values are applied correctly."""
        parser = create_argument_parser()
        
        # Test minimal trending command
        args = parser.parse_args(['trending'])
        assert args.timeframe == 'day'  # default
        assert args.limit == 20  # default
        assert args.format == 'csv'  # default
        assert args.analyze is False  # default
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_invalid_timeframe_handling(self, mock_api_class, mock_api):
        """Test handling of invalid timeframe values."""
        # argparse should catch invalid choices before we even reach our code
        parser = create_argument_parser()
        
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['trending', '--timeframe', 'invalid'])
        
        # SystemExit with code 2 indicates argument parsing error
        assert exc_info.value.code == 2
    
    def test_required_arguments_validation(self):
        """Test that required arguments are enforced."""
        parser = create_argument_parser()
        
        # Video command requires video_id
        with pytest.raises(SystemExit):
            parser.parse_args(['video'])
        
        # Search command requires query
        with pytest.raises(SystemExit):
            parser.parse_args(['search'])
        
        # Channel command requires channel_id
        with pytest.raises(SystemExit):
            parser.parse_args(['channel'])


class TestCLIOutputFormats:
    """Test CLI output format handling and file generation."""
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_csv_export_functionality(self, mock_api_class, mock_api, temp_output_dir, monkeypatch):
        """Test CSV export creates valid files."""
        mock_api_class.return_value = mock_api
        monkeypatch.chdir(temp_output_dir)
        
        test_args = ['--format', 'csv', 'trending']
        
        with patch('sys.argv', ['bitchute'] + test_args):
            with patch('bitchute.cli.CLIDataManager.save_data') as mock_save:
                main()
        
        # Verify save_data was called with CSV format
        mock_save.assert_called_once()
        args, kwargs = mock_save.call_args
        assert 'csv' in args[2]  # formats argument
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_json_export_functionality(self, mock_api_class, mock_api, temp_output_dir, monkeypatch):
        """Test JSON export creates valid files."""
        mock_api_class.return_value = mock_api
        monkeypatch.chdir(temp_output_dir)
        
        test_args = ['--format', 'json', 'popular']
        
        with patch('sys.argv', ['bitchute'] + test_args):
            with patch('bitchute.cli.CLIDataManager.save_data') as mock_save:
                main()
        
        # Verify save_data was called with JSON format
        mock_save.assert_called_once()
        args, kwargs = mock_save.call_args
        assert 'json' in args[2]  # formats argument
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_multiple_format_specification(self, mock_api_class, mock_api, temp_output_dir, monkeypatch):
        """Test multiple format specification creates all requested files."""
        mock_api_class.return_value = mock_api
        monkeypatch.chdir(temp_output_dir)
        
        test_args = ['--format', 'csv,json,xlsx', 'recent']
        
        with patch('sys.argv', ['bitchute'] + test_args):
            with patch('bitchute.cli.CLIDataManager.save_data') as mock_save:
                main()
        
        # Verify save_data was called with all formats
        mock_save.assert_called_once()
        args, kwargs = mock_save.call_args
        formats = args[2]
        assert 'csv' in formats
        assert 'json' in formats
        assert 'xlsx' in formats
    
    def test_file_naming_with_timestamps(self, temp_output_dir):
        """Test file naming includes timestamps."""
        # Create sample data
        df = pd.DataFrame([{'col1': 'value1', 'col2': 'value2'}])
        
        # Save with CLIDataManager
        manager = CLIDataManager()
        
        # Change to temp directory
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(temp_output_dir)
            
            with patch('bitchute.utils.DataExporter.export_data') as mock_export:
                mock_export.return_value = {'csv': 'test_data_20241201_120000.csv'}
                manager.save_data(df, 'test_data', ['csv'])
            
        finally:
            os.chdir(original_cwd)


class TestCLIErrorHandling:
    """Test CLI error handling and exit codes."""
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_invalid_video_id_handling(self, mock_api_class, mock_api):
        """Test handling of invalid video IDs."""
        mock_api_class.return_value = mock_api
        mock_api.get_video_info.return_value = pd.DataFrame()  # Empty result
        
        test_args = ['video', 'invalid_id']
        
        with patch('sys.argv', ['bitchute'] + test_args):
            result = main()
        
        assert result == 1  # Error exit code
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_api_error_handling(self, mock_api_class, mock_api):
        """Test handling of API errors."""
        mock_api_class.return_value = mock_api
        mock_api.get_trending_videos.side_effect = BitChuteAPIError("API Error", 500)
        
        test_args = ['trending']
        
        with patch('sys.argv', ['bitchute'] + test_args):
            result = main()
        
        assert result == 1  # Error exit code
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_validation_error_handling(self, mock_api_class, mock_api):
        """Test handling of validation errors."""
        mock_api_class.return_value = mock_api
        mock_api.search_videos.side_effect = ValidationError("Invalid query", "query")
        
        test_args = ['search', '']  # Empty query
        
        with patch('sys.argv', ['bitchute'] + test_args):
            result = main()
        
        assert result == 1  # Error exit code
    
    def test_missing_command_handling(self):
        """Test handling when no command is provided."""
        with patch('sys.argv', ['bitchute']):
            result = main()
        
        assert result == 0  # Shows help, exits successfully
    
    @patch('bitchute.cli.BitChuteAPI')
    def test_keyboard_interrupt_handling(self, mock_api_class, mock_api):
        """Test graceful handling of keyboard interrupts."""
        mock_api_class.return_value = mock_api
        mock_api.get_trending_videos.side_effect = KeyboardInterrupt()
        
        test_args = ['trending']
        
        with patch('sys.argv', ['bitchute'] + test_args):
            result = main()
        
        assert result == 1  # Error exit code
    
    def test_file_permission_error_handling(self, temp_output_dir):
        """Test handling of file permission errors."""
        # Create a mock scenario where save fails due to permissions
        df = pd.DataFrame([{'col1': 'value1'}])
        manager = CLIDataManager()
        
        # Mock DataExporter to raise PermissionError
        with patch('bitchute.cli.DataExporter.export_data') as mock_export:
            mock_export.side_effect = PermissionError("Permission denied")
            
            # Should handle permission error gracefully without crashing
            try:
                manager.save_data(df, 'test_file', ['csv'], verbose=True)
                # No exception should propagate
            except PermissionError:
                pytest.fail("PermissionError should be handled gracefully")


class TestCLIResultPrinter:
    """Test CLI result printing and formatting."""
    
    def test_video_results_printing(self, capsys):
        """Test video results are printed correctly."""
        df = pd.DataFrame([
            {
                'title': 'Test Video 1',
                'view_count': 1500,
                'channel_name': 'Test Channel',
                'duration': '12:34'
            },
            {
                'title': 'Test Video 2',
                'view_count': 2300,
                'channel_name': 'News Channel',
                'duration': '8:45'
            }
        ])
        
        CLIResultPrinter.print_video_results(df, "Test Videos")
        captured = capsys.readouterr()
        
        assert "Test Videos" in captured.out
        assert "Total: 2 videos" in captured.out
        assert "Test Video 1" in captured.out
        assert "1,500 views" in captured.out
    
    def test_channel_results_printing(self, capsys):
        """Test channel results are printed correctly."""
        df = pd.DataFrame([
            {
                'name': 'Test Channel',
                'video_count': 50,
                'subscriber_count': '1.2K'
            }
        ])
        
        CLIResultPrinter.print_channel_results(df, "Test Channels")
        captured = capsys.readouterr()
        
        assert "Test Channels" in captured.out
        assert "Total: 1 channels" in captured.out
        assert "Test Channel" in captured.out
    
    def test_hashtag_results_printing(self, capsys):
        """Test hashtag results are printed correctly."""
        df = pd.DataFrame([
            {'name': 'bitcoin', 'rank': 1},
            {'name': 'crypto', 'rank': 2}
        ])
        
        CLIResultPrinter.print_hashtag_results(df, "Trending Hashtags")
        captured = capsys.readouterr()
        
        assert "Trending Hashtags" in captured.out
        assert "Total: 2 hashtags" in captured.out
        assert "#bitcoin" in captured.out
        assert "#crypto" in captured.out
    
    def test_empty_results_handling(self, capsys):
        """Test handling of empty result sets."""
        empty_df = pd.DataFrame()
        
        CLIResultPrinter.print_video_results(empty_df, "Empty Results")
        captured = capsys.readouterr()
        
        assert "No empty results found" in captured.out


class TestCLIHelpText:
    """Test CLI help text and documentation."""
    
    def test_help_text_display(self, capsys):
        """Test help text is displayed correctly."""
        parser = create_argument_parser()
        
        with pytest.raises(SystemExit):
            parser.parse_args(['--help'])
    
    def test_command_help_text(self, capsys):
        """Test individual command help text."""
        parser = create_argument_parser()
        
        # Test trending command help
        with pytest.raises(SystemExit):
            parser.parse_args(['trending', '--help'])
    
    def test_examples_in_help(self):
        """Test that help includes usage examples."""
        parser = create_argument_parser()
        help_text = parser.format_help()
        
        assert "Examples:" in help_text
        assert "trending --timeframe day" in help_text
        assert "search" in help_text


class TestCLIDataManager:
    """Test CLI data management utilities."""
    
    def test_save_data_with_formats(self, temp_output_dir):
        """Test save_data method with different formats."""
        df = pd.DataFrame([{'col1': 'value1', 'col2': 'value2'}])
        manager = CLIDataManager()
        
        with patch('bitchute.utils.DataExporter.export_data') as mock_export:
            mock_export.return_value = {
                'csv': str(temp_output_dir / 'test.csv'),
                'json': str(temp_output_dir / 'test.json')
            }
            
            manager.save_data(df, 'test_data', ['csv', 'json'], verbose=True)
            
            mock_export.assert_called_once()
    
    def test_analyze_data_with_valid_data(self):
        """Test analyze_data method with valid DataFrame."""
        df = pd.DataFrame([
            {'view_count': 1000, 'like_count': 50, 'dislike_count': 5},
            {'view_count': 2000, 'like_count': 100, 'dislike_count': 10}
        ])
        
        manager = CLIDataManager()
        
        with patch('bitchute.utils.DataAnalyzer.analyze_videos') as mock_analyze:
            mock_analyze.return_value = {'total_videos': 2, 'views': {'total': 3000}}
            
            manager.analyze_data(df, show_analysis=True)
            
            mock_analyze.assert_called_once_with(df)
    
    def test_analyze_data_with_empty_data(self):
        """Test analyze_data method with empty DataFrame."""
        empty_df = pd.DataFrame()
        manager = CLIDataManager()
        
        # Should not crash with empty data
        manager.analyze_data(empty_df, show_analysis=True)