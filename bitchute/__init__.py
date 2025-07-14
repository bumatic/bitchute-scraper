"""
BitChute Scraper
"""

from .core import BitChuteAPI, SensitivityLevel, SortOrder, VideoSelection
from .models import Video, Channel, Hashtag, SearchResult, APIStats
from .exceptions import (
    BitChuteAPIError,
    TokenExtractionError,
    RateLimitError,
    ValidationError,
    AuthenticationError,
    NetworkError,
    DataProcessingError,
    ConfigurationError
)
from .token_manager import TokenManager
from .validators import InputValidator
from .utils import (
    DataProcessor,
    RateLimiter,
    RequestBuilder,
    PaginationHelper,
    BulkProcessor,
    DataExporter,
    DataAnalyzer,
    ContentFilter,
    CacheManager
)

__version__ = "2.0.0"
__author__ = "Marcus Burkhardt"
__email__ = "marcus.burkhardt@gmail.com"
__description__ = "A modern, API-based package to scrape BitChute platform data."
__url__ = "https://github.com/bumatic/bitchute-scraper"

# Main API class for easy access
API = BitChuteAPI

# Convenience imports for common usage patterns
__all__ = [
    # Core API
    'BitChuteAPI',
    'API',
    
    # Enums
    'SensitivityLevel',
    'SortOrder', 
    'VideoSelection',
    
    # Data Models
    'Video',
    'Channel',
    'Hashtag',
    'SearchResult',
    'APIStats',
    
    # Exceptions
    'BitChuteAPIError',
    'TokenExtractionError',
    'RateLimitError',
    'ValidationError',
    'AuthenticationError',
    'NetworkError',
    'DataProcessingError',
    'ConfigurationError',
    
    # Core Components
    'TokenManager',
    'InputValidator',
    
    # Utility Classes
    'DataProcessor',
    'RateLimiter',
    'RequestBuilder',
    'PaginationHelper',
    'BulkProcessor',
    'DataExporter',
    'DataAnalyzer',
    'ContentFilter',
    'CacheManager'
]

# Package metadata
__package_info__ = {
    'name': 'bitchute-scraper',
    'version': __version__,
    'author': __author__,
    'email': __email__,
    'description': __description__,
    'url': __url__,
    'python_requires': '>=3.7',
    'license': 'MIT',
    'keywords': ['bitchute', 'api', 'scraper', 'video', 'data-collection'],
    'classifiers': [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
}


def get_version():
    """Get package version"""
    return __version__


def get_package_info():
    """Get complete package information"""
    return __package_info__.copy()


# Quick start examples in docstring
__doc__ = """
BitChute API Scraper - Modern Python Package

A fast, reliable, and feature-rich package for scraping BitChute platform data
using official API endpoints. No more HTML parsing or browser automation for
basic data collection.

Quick Start:
    >>> import bitchute
    >>> 
    >>> # Initialize API client
    >>> api = bitchute.BitChuteAPI(verbose=True)
    >>> 
    >>> # Get trending videos (default: 50 videos)
    >>> trending = api.get_trending_videos('day')
    >>> print(f"Found {len(trending)} trending videos")
    >>> 
    >>> # Get all recent videos (default: 1000 videos)
    >>> all_videos = api.get_all_videos()
    >>> print(f"Found {len(all_videos)} videos")
    >>> 
    >>> # Search for videos (default: 50 results)
    >>> results = api.search_videos('climate change')
    >>> print(f"Found {len(results)} search results")
    >>> 
    >>> # Get video details
    >>> video = api.get_video_details('CLrgZP4RWyly', include_counts=True)
    >>> print(f"Video: {video.title} - {video.view_count:,} views")
    >>> 
    >>> # Export data
    >>> from bitchute.utils import DataExporter
    >>> exporter = DataExporter()
    >>> exporter.export_data(all_videos, 'all_videos', ['csv', 'json'])

Features:
    - Fast API-based data collection (10x faster than HTML parsing)
    - Automatic pagination for all endpoints
    - Comprehensive data models with computed properties
    - Robust error handling and retry logic
    - Built-in rate limiting and request optimization
    - Token management with multiple fallback methods
    - Data export to multiple formats (CSV, JSON, Excel, Parquet)
    - Advanced filtering and analysis tools
    - Concurrent processing for bulk operations
    - Command-line interface for easy usage
    - Extensive test coverage

Available Endpoints:
    - Trending videos (day/week/month) - with pagination
    - Popular videos - with pagination
    - Recent videos - with pagination
    - All videos (convenience method for large datasets)
    - Short videos - with pagination
    - Member picked videos
    - Video search with filters - with pagination
    - Channel search - with pagination
    - Trending hashtags - with pagination
    - Video details with engagement metrics
    - Bulk video processing

Data Models:
    - Video: Complete video metadata with engagement metrics
    - Channel: Channel information with computed statistics
    - Hashtag: Trending hashtags with rankings
    - SearchResult: Search result containers
    - APIStats: Usage statistics and monitoring

Error Handling:
    - BitChuteAPIError: General API errors
    - ValidationError: Input validation errors
    - RateLimitError: Rate limiting errors
    - TokenExtractionError: Authentication issues
    - NetworkError: Network-related errors

Default Parameters:
    - All methods default to retrieving 50 items
    - Pagination is automatic with 50 items per page
    - Use get_all_videos() for large datasets (default: 1000 videos)

Advanced Usage:
    >>> # Get 500 videos with custom page size
    >>> videos = api.get_recent_videos(limit=500, per_page=100)
    >>> 
    >>> # Search with specific sort order
    >>> from bitchute import SortOrder
    >>> results = api.search_videos('bitcoin', sort=SortOrder.VIEWS, limit=200)
    >>> 
    >>> # Filter and analyze data
    >>> from bitchute.utils import ContentFilter, DataAnalyzer
    >>> filter = ContentFilter()
    >>> filtered = filter.filter_by_views(videos, min_views=1000)
    >>> 
    >>> analyzer = DataAnalyzer()
    >>> stats = analyzer.analyze_videos(filtered)

For more information, examples, and documentation:
    https://github.com/bumatic/bitchute-scraper
"""