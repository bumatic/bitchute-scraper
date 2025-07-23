[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5643102.svg)](https://doi.org/10.5281/zenodo.5643102)

# BitChute Scraper

Python scraper for the BitChute video platform. It allows you to query for videos and to retrieve platform recommendations such as trending videos, popular videos (now called "fresh") or trending tags. The release of version 1.0.0 is a major update using an API approach to data collection compared to the Selenium based scraper of now defunct previous versions. Since the codebase was completely rewritten in collaboration with Claude AI backwards compatibility is not provided.

## Features

- **Fast API-based data collection** - 10x faster than HTML parsing approaches
- **Intelligent content deduplication** - Never download the same file twice
- **Automatic media downloads** - Thumbnails and videos with smart caching
- **Comprehensive data models** - Videos, channels, hashtags with computed properties
- **Concurrent processing** - Parallel requests with configurable rate limiting
- **Multiple export formats** - CSV, JSON, Excel, Parquet with timestamps
- **Command-line interface** - Easy automation and scripting support
- **Robust error handling** - Automatic retries and graceful fallbacks
- **Advanced monitoring** - Real-time statistics and performance tracking
- **Token debugging tools** - Resolve authentication issues automatically

## Installation

Install from PyPI:

```bash
pip3 install bitchute-scraper
```

For full functionality including progress bars and fast data formats:

```bash
pip install bitchute-scraper[full]
```

### System Requirements

- Python 3.7+
- Google Chrome or Chromium browser
- ChromeDriver (auto-managed)

## Quick Start

### Basic Usage

```python
import bitchute

# Initialize API client
api = bitchute.BitChuteAPI(verbose=True)

# Get trending videos
trending = api.get_trending_videos('day', limit=50)
print(f"Retrieved {len(trending)} trending videos")

# Search for videos
results = api.search_videos('climate change', limit=100)

# Get video details
video_info = api.get_video_info('VIDEO_ID', include_counts=True)
```

### Download Support

```python
# Initialize with downloads enabled
api = bitchute.BitChuteAPI(
    enable_downloads=True,
    download_base_dir="downloads",
    verbose=True
)

# Download videos with thumbnails
videos = api.get_trending_videos(
    'week',
    limit=20,
    download_thumbnails=True,
    download_videos=True
)
```

### Data Export

```python
from bitchute.utils import DataExporter

# Get data and export to multiple formats
videos = api.get_popular_videos(limit=100)

exporter = DataExporter()
exported_files = exporter.export_data(
    videos, 
    'popular_videos', 
    ['csv', 'json', 'xlsx']
)
```

### Real-time Statistics Monitoring

```python
combined_stats = api.get_combined_stats()

api.print_stats_summary(show_detailed=True)
```

### Database Management

```python
# Get database information
db_info = api.get_download_database_info()
print(f"Database contains {db_info['total_entries']} unique items")
print(f"Total storage tracked: {db_info['total_size_formatted']}")

# Clean up orphaned entries
api.cleanup_download_database(verify_files=True)

# Reset statistics for new measurement period
api.reset_download_stats()
```

### Command Line Interface

```bash
# Get trending videos
bitchute trending --timeframe day --limit 50 --format csv

# Search videos with details
bitchute search "bitcoin" --limit 100 --sort views --analyze

# Export to Excel
bitchute popular --limit 200 --format xlsx --analyze
```

## API Overview

### Core Methods

**Platform Recommendations:**
- `get_trending_videos(timeframe, limit)` - Trending by day/week/month
- `get_popular_videos(limit)` - Popular videos
- `get_recent_videos(limit)` - Most recent uploads
- `get_short_videos(limit)` - Short-form content

**Search Functions:**
- `search_videos(query, sensitivity, sort, limit)` - Video search
- `search_channels(query, sensitivity, limit)` - Channel search

**Individual Items:**
- `get_video_info(video_id, include_counts, include_media)` - Single video details
- `get_channel_info(channel_id)` - Channel information

**Hashtags:**
- `get_trending_hashtags(limit)` - Trending hashtags
- `get_videos_by_hashtag(hashtag, limit)` - Videos by hashtag

**Statistics & Monitoring:**
- `get_download_stats()` - Download performance metrics
- `get_combined_stats()` - Comprehensive API and download statistics
- `print_stats_summary()` - Formatted statistics display
- `reset_download_stats()` - Reset performance counters

**Troubleshooting:**
- `debug_token_issues()` - Comprehensive authentication diagnosis
- `fix_token_issues()` - Automatic token issue resolution
- `cleanup_download_database()` - Database maintenance

### Configuration Options

```python
api = bitchute.BitChuteAPI(
    verbose=True,                    # Enable logging
    enable_downloads=True,           # Enable media downloads
    download_base_dir="data",        # Download directory
    max_concurrent_downloads=5,      # Concurrent downloads
    force_redownload=False,          # Skip existing files
    rate_limit=0.3,                 # Seconds between requests
    timeout=60,                     # Request timeout
    cache_tokens=True               # Cache authentication tokens
)
```

### Data Models

All methods return pandas DataFrames with consistent schemas:

- **Video**: Complete metadata with engagement metrics and download paths
- **Channel**: Channel information with statistics and social links
- **Hashtag**: Trending hashtags with rankings and video counts

## Advanced Usage

### Bulk Data Collection

```python
# Get large datasets efficiently
all_videos = api.get_all_videos(limit=5000, include_details=True)

# Process with filtering
from bitchute.utils import ContentFilter
filtered = ContentFilter.filter_by_views(all_videos, min_views=1000)
crypto_videos = ContentFilter.filter_by_keywords(filtered, ['bitcoin', 'crypto'])
```

### Performance Monitoring

```python
# Track download performance
stats = api.get_download_stats()
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"Total downloaded: {stats['total_bytes_formatted']}")
```

## Troubleshooting Authentication Issues

### Common Token Problems

**Symptoms:**
- "Token invalid, attempting refresh" messages
- All extraction methods failing
- Cached token corruption
- API requests returning 401/403 errors

### Automatic Diagnosis and Recovery

```python
# Step 1: Run comprehensive diagnosis
api = bitchute.BitChuteAPI(verbose=True)
debug_info = api.debug_token_issues()

# Step 2: Attempt automatic fix
if not debug_info['token_info']['is_valid']:
    print("🔧 Attempting automatic recovery...")
    token = api.fix_token_issues()
    
    if token:
        print("✅ Recovery successful!")
    else:
        print("❌ Manual intervention required")

# Step 3: Manual troubleshooting if needed
if not token:
    print("\n🔍 Manual troubleshooting steps:")
    for recommendation in debug_info['recommendations']:
        print(f"   • {recommendation}")
```

### Manual Resolution Steps

```python
# Clear all caches and retry
api.token_manager.clear_all_caches()
token = api.get_token()

# Test specific token
if token:
    validation_results = api.token_manager.test_token_validation(token)
    print(f"Token validation: {validation_results}")

# Force fresh extraction
api.token_manager.invalidate_token()
new_token = api.token_manager.get_token()
```

## Documentation

- **API Reference**: Complete method documentation with examples
- **User Guide**: Detailed tutorials and best practices
- **CLI Reference**: Command-line usage and automation examples

## Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Development Setup

```bash
git clone https://github.com/bumatic/bitchute-scraper.git
cd bitchute-scraper
pip install -e .[dev]
pytest
```

## License

MIT License - see LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/bumatic/bitchute-scraper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bumatic/bitchute-scraper/discussions)


## Disclaimer

This software is intended for educational and research purposes only.
Users are responsible for complying with Terms of Service and all applicable laws. 
The software authors disclaim all liability for any misuse of this software.

## Version History

### v1.0.1 - Media Download Deduplication & Enhanced Monitoring
- **Content-based deduplication system on the basis of a persistent download database**
- **Comprehensive statistics and monitoring**
- **Advanced token debugging tools**

### v1.0.0 - API-Based Architecture
- **Fast API-based data collection**
- **Automatic media downloads**
- **Concurrent processing**
- **Multiple export formats**
- **Command-line interface**
