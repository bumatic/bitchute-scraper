"""
BitChute Scraper

API-based package to scrape BitChute platform data.

This package provides a fast, reliable interface to BitChute's platform data
with support for automatic media downloads, and concurrent processing.

Example:
    Basic usage:
        >>> import bitchute
        >>> api = bitchute.BitChuteAPI(verbose=True)
        >>> trending = api.get_trending_videos('day', limit=10)
        >>> print(f"Found {len(trending)} trending videos")

    With downloads enabled:
        >>> api = bitchute.BitChuteAPI(
        ...     enable_downloads=True,
        ...     download_base_dir="my_downloads",
        ...     verbose=True
        ... )
        >>> videos = api.get_trending_videos(
        ...     'day',
        ...     limit=10,
        ...     download_thumbnails=True
        ... )

    Advanced usage:
        >>> results = api.search_videos(
        ...     'climate change',
        ...     limit=50,
        ...     include_details=True,
        ...     download_thumbnails=True
        ... )
        >>> from bitchute.utils import DataExporter
        >>> exporter = DataExporter()
        >>> exporter.export_data(results, 'search_results', ['csv', 'json'])
"""

from .core import BitChuteAPI, SensitivityLevel, SortOrder, VideoSelection
from .models import Video, Channel, Hashtag, SearchResult, APIStats, DownloadResult
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
from .download_manager import MediaDownloadManager
from .utils import (
    DataProcessor,
    RateLimiter,
    RequestBuilder,
    PaginationHelper,
    BulkProcessor,
    DataExporter,
    ContentFilter,
    CacheManager
)

__version__ = "1.0.0"
__author__ = "Marcus Burkhardt"
__email__ = "marcus.burkhardt@gmail.com"
__description__ = "A modern, API-based package to scrape BitChute platform data with automatic download capabilities."
__url__ = "https://github.com/bumatic/bitchute-scraper"

# Main API class for convenient access
API = BitChuteAPI

# Public API exports
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
    'DownloadResult',
    
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
    'MediaDownloadManager',
    
    # Utility Classes
    'DataProcessor',
    'RateLimiter',
    'RequestBuilder',
    'PaginationHelper',
    'BulkProcessor',
    'DataExporter',
    'ContentFilter',
    'CacheManager'
]

# Package metadata for programmatic access
__package_info__ = {
    'name': 'bitchute-scraper',
    'version': __version__,
    'author': __author__,
    'email': __email__,
    'description': __description__,
    'url': __url__,
    'python_requires': '>=3.7',
    'license': 'MIT',
    'keywords': ['bitchute', 'api', 'scraper', 'video', 'data-collection', 'download', 'media'],
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
        'Topic :: Multimedia :: Video',
        'Topic :: Internet :: File Transfer Protocol (FTP)',
    ]
}


def get_version():
    """Get the current package version.
    
    Returns:
        str: The package version string.
        
    Example:
        >>> import bitchute
        >>> print(bitchute.get_version())
        '1.0.0'
    """
    return __version__


def get_package_info():
    """Get complete package information dictionary.
    
    Returns:
        dict: Dictionary containing package metadata including name, version,
            author, description, requirements, and classifiers.
            
    Example:
        >>> import bitchute
        >>> info = bitchute.get_package_info()
        >>> print(info['name'])
        'bitchute-scraper'
        >>> print(info['python_requires'])
        '>=3.7'
    """
    return __package_info__.copy()


# Module-level documentation string for comprehensive usage guidance
__doc__ = """
BitChute API Scraper - Modern Python Package with Download Support

A fast, reliable, and feature-rich package for scraping BitChute platform data
using official API endpoints with automatic thumbnail and video download capabilities.

Features:
    - Fast API-based data collection (10x faster than HTML parsing)
    - Automatic pagination for all endpoints
    - Comprehensive data models with computed properties
    - Robust error handling and retry logic
    - Built-in rate limiting and request optimization
    - Token management with multiple fallback methods
    - Smart file downloads with caching and progress tracking
    - Data export to multiple formats (CSV, JSON, Excel, Parquet)
    - Advanced filtering and analysis tools
    - Concurrent processing for bulk operations
    - Command-line interface for easy usage
    - Extensive test coverage

Quick Start Guide:

    Basic Usage:
        >>> import bitchute
        >>> 
        >>> # Initialize API client
        >>> api = bitchute.BitChuteAPI(verbose=True)
        >>> 
        >>> # Get trending videos
        >>> trending = api.get_trending_videos('day', limit=10)
        >>> print(f"Found {len(trending)} trending videos")
        >>> 
        >>> # Search for videos
        >>> results = api.search_videos('bitcoin', limit=50)
        >>> 
        >>> # Get video details
        >>> video_df = api.get_video_info('CLrgZP4RWyly', include_counts=True)

    With Downloads Enabled:
        >>> # Initialize with downloads
        >>> api = bitchute.BitChuteAPI(
        ...     enable_downloads=True,
        ...     download_base_dir="bitchute_data",
        ...     verbose=True
        ... )
        >>> 
        >>> # Get videos with thumbnails
        >>> trending = api.get_trending_videos(
        ...     'day',
        ...     limit=10,
        ...     download_thumbnails=True
        ... )
        >>> 
        >>> # Get videos with full downloads
        >>> videos = api.get_popular_videos(
        ...     limit=20,
        ...     include_details=True,
        ...     download_thumbnails=True,
        ...     download_videos=True
        ... )

    Advanced Configuration:
        >>> api = bitchute.BitChuteAPI(
        ...     enable_downloads=True,
        ...     download_base_dir="downloads",
        ...     thumbnail_folder="thumbs",
        ...     video_folder="videos",
        ...     force_redownload=False,
        ...     max_concurrent_downloads=5,
        ...     rate_limit=0.3,
        ...     timeout=60,
        ...     verbose=True
        ... )

    Data Export:
        >>> from bitchute.utils import DataExporter
        >>> 
        >>> # Get data
        >>> videos = api.get_recent_videos(limit=100, download_thumbnails=True)
        >>> 
        >>> # Export to multiple formats
        >>> exporter = DataExporter()
        >>> exporter.export_data(videos, 'recent_videos', ['csv', 'json', 'xlsx'])

Available Endpoints:
    Platform Recommendations:
        - get_trending_videos(timeframe, limit) - Trending videos by day/week/month
        - get_popular_videos(limit) - Popular videos
        - get_recent_videos(limit) - Most recent videos
        - get_all_videos(limit) - Bulk recent video retrieval
        - get_short_videos(limit) - Short-form videos
        - get_member_picked_videos(limit) - Member-liked content
	- get_trending_hashtags(limit) - Trending hashtags
        - get_videos_by_hashtag(hashtag, limit) - Videos for specific hashtag

    Search Functions:
        - search_videos(query, sensitivity, sort, limit) - Video search
        - search_channels(query, sensitivity, limit) - Channel search

    Individual Items:
        - get_video_info(video_id, include_counts, include_media) - Single video details
        - get_channel_info(channel_id) - Channel information
        - get_channel_videos(channel_id, limit, order_by) - Videos from specific channel

Data Models:
    - Video: Complete video metadata with engagement metrics and download paths
    - Channel: Channel information with computed statistics
    - Hashtag: Trending hashtags with rankings
    - SearchResult: Search result containers
    - APIStats: Usage statistics and monitoring
    - DownloadResult: Download operation results

Error Handling:
    - BitChuteAPIError: General API errors
    - ValidationError: Input validation errors
    - RateLimitError: Rate limiting errors
    - TokenExtractionError: Authentication issues
    - NetworkError: Network-related errors
    - ConfigurationError: Download configuration errors

Download System Features:
    - File Naming: {video_id}_{title}_{timestamp}.{ext}
    - Conflict Resolution: Automatic incrementing (1), (2), etc.
    - Progress Tracking: Optional progress bars with tqdm
    - Concurrent Downloads: Configurable worker pool
    - Smart Caching: Skip existing files unless forced
    - Error Recovery: Graceful handling of failed downloads

Default Parameters:
    - All methods default to retrieving 50 items
    - Pagination is automatic with 50 items per page
    - Downloads are disabled by default (enable_downloads=False)
    - Use get_all_videos() for large datasets (default: 1000 videos)

Command Line Interface:
    Basic usage:
        $ bitchute trending --timeframe day --limit 50 --format csv
        $ bitchute search "climate change" --limit 100 --sort views
        $ bitchute popular --analyze --format xlsx

For more information, examples, and documentation:
    https://github.com/bumatic/bitchute-scraper
"""
