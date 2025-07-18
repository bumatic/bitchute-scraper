"""
BitChute Scraper
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
from .download_manager import MediaDownloadManager  # NEW
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
    'DownloadResult',  # NEW
    
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
    'MediaDownloadManager',  # NEW
    
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
    """Get package version"""
    return __version__


def get_package_info():
    """Get complete package information"""
    return __package_info__.copy()


# Quick start examples in docstring
__doc__ = """
BitChute API Scraper - Modern Python Package with Download Support

A fast, reliable, and feature-rich package for scraping BitChute platform data
using official API endpoints with automatic thumbnail and video download capabilities.

Quick Start:
    >>> import bitchute
    >>> 
    >>> # Initialize API client with downloads enabled
    >>> api = bitchute.BitChuteAPI(
    ...     enable_downloads=True,
    ...     download_base_dir="my_downloads",
    ...     verbose=True
    ... )
    >>> 
    >>> # Get trending videos with thumbnails downloaded
    >>> trending = api.get_trending_videos(
    ...     limit=10, 
    ...     download_thumbnails=True
    ... )
    >>> print(f"Downloaded {trending['has_local_thumbnail'].sum()} thumbnails")
    >>> 
    >>> # Get video details with full downloads
    >>> video_df = api.get_video_info(
    ...     'CLrgZP4RWyly',
    ...     include_counts=True,
    ...     download_thumbnails=True,
    ...     download_videos=True
    ... )
    >>> 
    >>> # Search with downloads
    >>> results = api.search_videos(
    ...     'climate change',
    ...     limit=20,
    ...     download_thumbnails=True
    ... )

Basic Usage (without downloads):
    >>> # Traditional usage still works
    >>> api = bitchute.BitChuteAPI(verbose=True)
    >>> 
    >>> # Get trending videos (DataFrame format for consistency)
    >>> trending = api.get_trending_videos('day', limit=50)
    >>> print(f"Found {len(trending)} trending videos")
    >>> 
    >>> # Get all recent videos
    >>> all_videos = api.get_all_videos(limit=1000)
    >>> 
    >>> # Search for videos
    >>> results = api.search_videos('bitcoin', limit=100)
    >>> 
    >>> # Get single video info (now returns DataFrame)
    >>> video_df = api.get_video_info('CLrgZP4RWyly', include_counts=True)
    >>> 
    >>> # Get Video object if needed
    >>> video_obj = api.get_video_object('CLrgZP4RWyly', include_counts=True)

Advanced Download Configuration:
    >>> api = bitchute.BitChuteAPI(
    ...     enable_downloads=True,
    ...     download_base_dir="bitchute_downloads",
    ...     thumbnail_folder="thumbs",
    ...     video_folder="videos", 
    ...     force_redownload=False,
    ...     max_concurrent_downloads=5,
    ...     verbose=True
    ... )
    >>> 
    >>> # Get videos with selective downloads
    >>> videos = api.get_popular_videos(
    ...     limit=50,
    ...     include_details=True,
    ...     download_thumbnails=True,
    ...     download_videos=False,  # Thumbnails only
    ...     force_redownload=True   # Override instance setting
    ... )
    >>> 
    >>> # Check download statistics
    >>> stats = api.get_download_stats()
    >>> print(f"Success rate: {stats['success_rate']:.1%}")

Export with Downloads:
    >>> from bitchute.utils import DataExporter
    >>> 
    >>> # Videos now include local file paths
    >>> df = api.get_recent_videos(limit=100, download_thumbnails=True)
    >>> 
    >>> # Export includes download paths
    >>> exporter = DataExporter()
    >>> exporter.export_data(df, 'videos_with_thumbnails', ['csv', 'json'])

New Features in v1.1.0:
    ✨ Automatic thumbnail and video downloads
    ✨ Smart file caching and conflict resolution  
    ✨ Concurrent download processing
    ✨ Progress tracking with tqdm support
    ✨ Return type consistency (all video methods → DataFrames)
    ✨ Backward compatibility with get_video_object() methods
    ✨ Enhanced DataFrame schema with download paths
    ✨ Download statistics and monitoring

Breaking Changes in v1.1.0:
    ⚠️  get_video_info() now returns DataFrame instead of Video object
    ⚠️  get_channel_info() now returns DataFrame instead of Channel object
    ✅ Use get_video_object() and get_channel_object() for object access
    ✅ All video methods now have consistent DataFrame returns
    ✅ New download parameters added to all video methods

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

Available Endpoints:
    - Trending videos (day/week/month) - with pagination and downloads
    - Popular videos - with pagination and downloads
    - Recent videos - with pagination and downloads
    - All videos (convenience method for large datasets) - with downloads
    - Short videos - with pagination and downloads
    - Member picked videos - with downloads
    - Video search with filters - with pagination and downloads
    - Channel search - with pagination
    - Trending hashtags - with pagination
    - Video details with engagement metrics - with downloads
    - Channel details
    - Bulk video processing with downloads

Data Models:
    - Video: Complete video metadata with engagement metrics and download paths
    - Channel: Channel information with computed statistics
    - Hashtag: Trending hashtags with rankings
    - SearchResult: Search result containers
    - APIStats: Usage statistics and monitoring
    - DownloadResult: Download operation results (NEW)

Error Handling:
    - BitChuteAPIError: General API errors
    - ValidationError: Input validation errors
    - RateLimitError: Rate limiting errors
    - TokenExtractionError: Authentication issues
    - NetworkError: Network-related errors
    - ConfigurationError: Download configuration errors (NEW)

Download System:
    - File Naming: {video_id}_{title}_{timestamp}.{ext}
    - Conflict Resolution: Automatic incrementing (1), (2), etc.
    - Progress Tracking: Optional tqdm progress bars
    - Concurrent Downloads: Configurable worker pool
    - Smart Caching: Skip existing files unless forced
    - Error Recovery: Graceful handling of failed downloads

Default Parameters:
    - All methods default to retrieving 50 items
    - Pagination is automatic with 50 items per page
    - Downloads are disabled by default (enable_downloads=False)
    - Use get_all_videos() for large datasets (default: 1000 videos)

Migration Guide:
    # OLD: Object returns
    video = api.get_video_info('video_id')  # Returned Video object
    
    # NEW: DataFrame returns (recommended)
    video_df = api.get_video_info('video_id')  # Returns single-row DataFrame
    
    # NEW: Object access (if needed)
    video_obj = api.get_video_object('video_id')  # Returns Video object
    
    # Download-enabled usage
    video_df = api.get_video_info(
        'video_id', 
        download_thumbnails=True,
        download_videos=True
    )

For more information, examples, and documentation:
    https://github.com/bumatic/bitchute-scraper
"""