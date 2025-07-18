[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5539420.svg)](https://doi.org/10.5281/zenodo.5539420)

# BitChute Scraper

Python scraper for the BitChute video platform. It allows you to query for videos and to retrieve platform recommendations such as trending videos, popular videos (now called "fresh") or trending tags. The release of version 1.0.0 is a major update using an API approach to data collection compared to the Selenium based scraper of now defunct previous versions. Since the codebase was completely rewritten in collaboration with Claude AI backwards compatibility is not provided.

## Installation

bitchute-scraper is available on PyPi:

```Shell
$ pip3 install bitchute-scraper
```

Alternatively you can download the repository and install the package by running the setup.py install routine. Make sure to install the requirements as well:

```Shell
$ pip3 install -r requirements.txt
$ python3 setup.py install
```

Additionally this package requires Google Chrome and chromedriver to be installed on your system. Make sure that they are available.

```bash
brew install --cask google-chrome
brew install chromedriver
```

In addition to the python package the scraper makes use of the selenium chromedriver which is an application that programmatically controls the Google Chrome browser. While the package uses the webdriver-manager to ensure that the proper webdriver is installed on your system you need to make sure that Google Chrome is installed. On macOS you can install both easily with homebrew:

```bash
brew install --cask google-chrome
```

On Linux and Windows installing Google Chrome should be straight forward as well. In case you don't know how to do this, just query it with the search engine of your trust!

## Usage (v1.0.0+)

The package has been completely rewritten with an API-based approach for better performance and reliability.

### Quick Start

```python
import bitchute

# Initialize API client
api = bitchute.BitChuteAPI(verbose=True)

# Get trending videos
trending = api.get_trending_videos('day')
print(f"Retrieved {len(trending)} videos")

# Search for videos
results = api.search_videos('bitcoin', limit=100)

# Get video details
video = api.get_video_info('CLrgZP4RWyly', include_counts=True)
```

### Download Support

```python
# Initialize with downloads enabled
api = bitchute.BitChuteAPI(
    enable_downloads=True,
    download_base_dir="downloads",
    verbose=True
)

# Download thumbnails and videos
videos = api.get_trending_videos(
    'day', 
    limit=10,
    download_thumbnails=True,
    download_videos=True
)
```

### Available Methods

**Video Collections:**
- `get_trending_videos(timeframe, limit)` - Trending videos by day/week/month
- `get_popular_videos(limit)` - Popular videos
- `get_recent_videos(limit)` - Most recent videos
- `get_all_videos(limit)` - Bulk recent video retrieval
- `get_short_videos(limit)` - Short-form videos
- `get_member_picked_videos(limit)` - Member-curated content

**Search:**
- `search_videos(query, sensitivity, sort, limit)` - Video search
- `search_channels(query, sensitivity, limit)` - Channel search

**Individual Items:**
- `get_video_info(video_id, include_counts, include_media)` - Single video details
- `get_channel_info(channel_id)` - Channel information
- `get_channel_videos(channel_id, limit, order_by)` - Videos from specific channel

**Hashtags:**
- `get_trending_hashtags(limit)` - Trending hashtags
- `get_videos_by_hashtag(hashtag, limit)` - Videos for specific hashtag

### Command Line Interface

```bash
# Get trending videos
bitchute trending --timeframe day --limit 50 --format csv

# Search videos
bitchute search "climate change" --limit 100 --sort views

# Export data
bitchute popular --analyze --format xlsx
```

### Data Export

All methods return pandas DataFrames that can be easily exported:

```python
from bitchute.utils import DataExporter

# Get data
videos = api.get_trending_videos('day', limit=100)

# Export to multiple formats
exporter = DataExporter()
exporter.export_data(videos, 'trending_videos', ['csv', 'json', 'xlsx'])
```

## Legacy Usage (Deprecated)

The original crawler interface is deprecated but still documented for reference:

```python
import bitchute as bc
b = bc.Crawler()        
trending_videos = b.get_trending_videos()

# Trending tags
trending_tags = b.get_trending_tags()

# Combined retrieval
trending_videos, trending_tags = b.get_trending()

# Other collections
popular_videos = b.get_popular_videos()
all_videos = b.get_all_videos()

# Channel operations
recommended_channels = b.get_recommended_channels(extended=False)
about, videos = b.get_channels(channel_ids, get_channel_about=True, get_channel_videos=True)

# Search
videos = search(query, top=100)
```

## Requirements

- Python 3.7+
- Google Chrome or Chromium browser
- ChromeDriver (auto-managed by webdriver-manager)

## License

MIT License - see LICENSE file for details.

## Contributing

Issues and pull requests welcome at the GitHub repository.