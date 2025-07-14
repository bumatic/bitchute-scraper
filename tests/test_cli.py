"""
Tests for CLI functionality
"""

import pytest
import argparse
from unittest.mock import Mock, patch
import pandas as pd
from io import StringIO

from bitchute.cli import CLIFormatter, create_argument_parser


class TestCLIFormatter:
    """Test CLI formatting functionality"""
    
    def test_success_formatting(self):
        """Test success message formatting"""
        message = "Operation completed"
        formatted = CLIFormatter.success(message)
        
        assert "✅" in formatted
        assert message in formatted
        assert CLIFormatter.COLORS['green'] in formatted
        assert CLIFormatter.COLORS['end'] in formatted
    
    def test_error_formatting(self):
        """Test error message formatting"""
        message = "Operation failed"
        formatted = CLIFormatter.error(message)
        
        assert "❌" in formatted
        assert message in formatted
        assert CLIFormatter.COLORS['red'] in formatted
    
    def test_warning_formatting(self):
        """Test warning message formatting"""
        message = "Warning message"
        formatted = CLIFormatter.warning(message)
        
        assert "⚠️" in formatted
        assert message in formatted
        assert CLIFormatter.COLORS['yellow'] in formatted


class TestArgumentParser:
    """Test argument parser functionality"""
    
    def test_create_argument_parser(self):
        """Test argument parser creation"""
        parser = create_argument_parser()
        
        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.description is not None
    
    def test_trending_command_parsing(self):
        """Test trending command parsing"""
        parser = create_argument_parser()
        
        # Test basic trending command
        args = parser.parse_args(['trending'])
        assert args.command == 'trending'
        assert args.timeframe == 'day'  # default
        assert args.limit == 20  # default
        
        # Test with options
        args = parser.parse_args(['trending', '--timeframe', 'week', '--limit', '50'])
        assert args.timeframe == 'week'
        assert args.limit == 50
    
    def test_search_command_parsing(self):
        """Test search command parsing"""
        parser = create_argument_parser()
        
        args = parser.parse_args(['search', 'test query'])
        assert args.command == 'search'
        assert args.query == 'test query'
        assert args.limit == 50  # default
        assert args.sort == 'new'  # default
    
    def test_video_command_parsing(self):
        """Test video command parsing"""
        parser = create_argument_parser()
        
        args = parser.parse_args(['video', 'CLrgZP4RWyly'])
        assert args.command == 'video'
        assert args.video_id == 'CLrgZP4RWyly'
        assert args.counts == False  # default
        assert args.media == False  # default
        
        # Test with flags
        args = parser.parse_args(['video', 'CLrgZP4RWyly', '--counts', '--media'])
        assert args.counts == True
        assert args.media == True
    
    def test_global_options_parsing(self):
        """Test global options parsing"""
        parser = create_argument_parser()
        
        args = parser.parse_args(['--verbose', '--format', 'csv,json', 'trending'])
        assert args.verbose == True
        assert args.format == 'csv,json'
        assert args.command == 'trending'
