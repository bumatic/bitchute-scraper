Quick Start
===========

This guide will get you up and running with BitChute Scraper in minutes.

Basic Usage
-----------

Initialize the API Client
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import bitchute
   
   # Basic initialization
   api = bitchute.BitChuteAPI(verbose=True)

Get Trending Videos
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get today's trending videos
   trending = api.get_trending_videos('day', limit=20)
   print(f"Found {len(trending)} trending videos")
   
   # Display top results
   print(trending[['title', 'view_count', 'channel_name']].head())

Search for Content
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Search for videos
   results = api.search_videos('climate change', limit=50)
   
   # Search channels
   channels = api.search_channels('news', limit=20)

Get Video Details
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get detailed information for a specific video
   video_info = api.get_video_info('VIDEO_ID', include_counts=True)
   print(video_info[['title', 'like_count', 'dislike_count']])

Working with Downloads
----------------------

Enable Downloads
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Initialize with download support
   api = bitchute.BitChuteAPI(
       enable_downloads=True,
       download_base_dir="downloads",
       verbose=True
   )

Download Thumbnails
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get videos with thumbnail downloads
   videos = api.get_trending_videos(
       'week',
       limit=10,
       download_thumbnails=True
   )
   
   # Check download status
   for _, video in videos.iterrows():
       if video['local_thumbnail_path']:
           print(f"Downloaded: {video['title']}")

Download Videos
~~~~~~~~~~~~~~~

.. code-block:: python

   # Download both thumbnails and videos
   videos = api.get_popular_videos(
       limit=5,
       download_thumbnails=True,
       download_videos=True
   )

Data Export
-----------

Export to CSV
~~~~~~~~~~~~~

.. code-block:: python

   from bitchute.utils import DataExporter
   
   # Get data
   videos = api.get_recent_videos(limit=100)
   
   # Export to CSV
   exporter = DataExporter()
   exported = exporter.export_data(videos, 'recent_videos', ['csv'])
   print(f"Exported to: {exported['csv']}")

Multiple Formats
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Export to multiple formats
   exported = exporter.export_data(
       videos, 
       'dataset',
       ['csv', 'json', 'xlsx']
   )
   
   for format_name, filepath in exported.items():
       print(f"{format_name.upper()}: {filepath}")

Command Line Usage
------------------

Basic Commands
~~~~~~~~~~~~~~

.. code-block:: bash

   # Get trending videos
   bitchute trending --timeframe day --limit 50
   
   # Search with analysis
   bitchute search "bitcoin" --limit 100 --analyze
   
   # Export to Excel
   bitchute popular --limit 200 --format xlsx

Advanced Commands
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Multiple formats with analysis
   bitchute trending --timeframe week --format csv,json,xlsx --analyze
   
   # Channel search
   bitchute channels "news" --limit 50 --format csv
   
   # Get hashtags
   bitchute hashtags --limit 100

Data Analysis
-------------

Basic Statistics
~~~~~~~~~~~~~~~~

.. code-block:: python

   from bitchute.utils import DataAnalyzer
   
   # Get and analyze data
   videos = api.get_trending_videos('day', limit=100)
   
   analyzer = DataAnalyzer()
   analysis = analyzer.analyze_videos(videos)
   
   print(f"Total views: {analysis['views']['total']:,}")
   print(f"Average views: {analysis['views']['average']:.0f}")
   print(f"Top channel: {list(analysis['top_channels'].keys())[0]}")

Content Filtering
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from bitchute.utils import ContentFilter
   
   # Filter by view count
   popular = ContentFilter.filter_by_views(
       videos, 
       min_views=1000, 
       max_views=100000
   )
   
   # Filter by keywords
   crypto_videos = ContentFilter.filter_by_keywords(
       videos, 
       ['bitcoin', 'cryptocurrency', 'crypto']
   )

Configuration Options
---------------------

API Client Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   api = bitchute.BitChuteAPI(
       verbose=True,                    # Enable detailed logging
       enable_downloads=True,           # Enable media downloads
       download_base_dir="data",        # Download directory
       max_concurrent_downloads=5,      # Concurrent download limit
       rate_limit=0.3,                 # Seconds between requests
       timeout=60,                     # Request timeout
       max_workers=8                   # Parallel processing workers
   )

Download Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   api = bitchute.BitChuteAPI(
       enable_downloads=True,
       download_base_dir="downloads",
       thumbnail_folder="thumbs",       # Subdirectory for thumbnails
       video_folder="videos",           # Subdirectory for videos
       force_redownload=False,          # Skip existing files
       max_concurrent_downloads=3       # Download concurrency
   )

Error Handling
--------------

Basic Error Handling
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from bitchute.exceptions import BitChuteAPIError, ValidationError
   
   try:
       videos = api.get_trending_videos('day', limit=50)
   except BitChuteAPIError as e:
       print(f"API error: {e}")
   except ValidationError as e:
       print(f"Validation error: {e}")

Performance Monitoring
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Check download statistics
   if api.enable_downloads:
       stats = api.get_download_stats()
       print(f"Success rate: {stats['success_rate']:.1%}")
       print(f"Downloaded: {stats['total_bytes_formatted']}")

Next Steps
----------

* Read the :doc:`tutorials/index` for detailed guides
* Explore the :doc:`api/core` for complete API reference
* Check :doc:`examples/basic_usage` for more examples
* Learn about :doc:`configuration` options