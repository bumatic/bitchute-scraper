"""
BitChute Scraper Test Suite

This package contains comprehensive tests for the BitChute API scraper.

Test Structure:
- test_core.py: Core API functionality tests
- test_models.py: Data model tests
- test_validators.py: Input validation tests
- test_utils.py: Utility function tests
- test_token_manager.py: Token management tests
- test_exceptions.py: Exception handling tests
- test_integration.py: Integration tests
- test_performance.py: Performance benchmarks
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test fixtures and utilities
from .fixtures import *
from .helpers import *

__all__ = [
    'create_mock_video_data',
    'create_mock_channel_data',
    'create_mock_api_response',
    'assert_valid_dataframe',
    'assert_valid_video',
    'assert_valid_channel'
]