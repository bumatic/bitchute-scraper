Command Line Interface
======================

BitChute Scraper provides a comprehensive command-line interface for easy automation and scripting. The CLI supports all major functionality including data collection, export, and analysis.

Installation and Setup
-----------------------

The CLI is automatically available after installing the package:

.. code-block:: bash

   pip install bitchute-scraper

Verify installation:

.. code-block:: bash

   bitchute --help

Basic Usage
-----------

The general command structure is:

.. code-block:: bash

   bitchute [COMMAND] [OPTIONS]

Available commands:

* ``trending`` - Get trending videos
* ``popular`` - Get popular videos  
* ``recent`` - Get recent videos
* ``search`` - Search videos
* ``channels`` - Search channels
* ``hashtags`` - Get trending hashtags
* ``video`` - Get video details
* ``channel`` - Get channel details
* ``channel-videos`` - Get videos from channel

Global Options
--------------

These options work with all commands:

``--verbose, -v``
   Enable verbose output with detailed logging

``--format, -f FORMAT``
   Output formats: csv,json,xlsx,parquet (comma-separated)
   Default: csv

``--analyze``
   Show comprehensive data analysis after collection

``--timeout SECONDS``
   Request timeout in seconds (default: 30)

Commands Reference
------------------

trending
~~~~~~~~

Get trending videos by timeframe.

.. code-block:: bash

   bitchute trending [OPTIONS]

Options:

``--timeframe, -t {day,week,month}``
   Trending timeframe (default: day)

``--limit, -l INTEGER``
   Number of videos to retrieve (default: 20)

``--offset INTEGER``
   Pagination offset (default: 0)

Examples:

.. code-block:: bash

   # Get today's top 50 trending videos
   bitchute trending --timeframe day --limit 50
   
   # Get weekly trending with analysis
   bitchute trending -t week -l 100 --analyze
   
   # Export to multiple formats
   bitchute trending --format csv,json,xlsx

popular
~~~~~~~

Get popular videos.

.. code-block:: bash

   bitchute popular [OPTIONS]

Options:

``--limit, -l INTEGER``
   Number of videos to retrieve (default: 30)

``--offset INTEGER``
   Pagination offset (default: 0)

Examples:

.. code-block:: bash

   # Get popular videos with analysis
   bitchute popular --limit 100 --analyze
   
   # Export to Excel
   bitchute popular --format xlsx

recent
~~~~~~

Get recent videos.

.. code-block:: bash

   bitchute recent [OPTIONS]

Options:

``--limit, -l INTEGER``
   Number of videos to retrieve (default: 30)

``--pages, -p INTEGER``
   Number of pages to fetch (default: 1)

Examples:

.. code-block:: bash

   # Get 150 recent videos (3 pages of 50)
   bitchute recent --limit 50 --pages 3
   
   # Get recent with detailed analysis
   bitchute recent -l 200 --analyze --format json

search
~~~~~~

Search for videos with filters.

.. code-block:: bash

   bitchute search QUERY [OPTIONS]

Arguments:

``QUERY``
   Search query string (required)

Options:

``--limit, -l INTEGER``
   Number of results to retrieve (default: 50)

``--sensitivity {normal,nsfw,nsfl}``
   Content sensitivity level (default: normal)

``--sort {new,old,views}``
   Sort order (default: new)

Examples:

.. code-block:: bash

   # Basic search
   bitchute search "climate change" --limit 100
   
   # Search sorted by views
   bitchute search "bitcoin" --sort views --limit 200
   
   # Search with analysis
   bitchute search "technology" --analyze --format xlsx

channels
~~~~~~~~

Search for channels.

.. code-block:: bash

   bitchute channels QUERY [OPTIONS]

Arguments:

``QUERY``
   Search query string (required)

Options:

``--limit, -l INTEGER``
   Number of results to retrieve (default: 50)

``--sensitivity {normal,nsfw,nsfl}``
   Content sensitivity level (default: normal)

Examples:

.. code-block:: bash

   # Search for news channels
   bitchute channels "news" --limit 50
   
   # Export channel data
   bitchute channels "technology" --format csv,json

hashtags
~~~~~~~~

Get trending hashtags.

.. code-block:: bash

   bitchute hashtags [OPTIONS]

Options:

``--limit, -l INTEGER``
   Number of hashtags to retrieve (default: 50)

Examples:

.. code-block:: bash

   # Get top 100 trending hashtags
   bitchute hashtags --limit 100
   
   # Export hashtag data
   bitchute hashtags --format json

video
~~~~~

Get detailed information for a specific video.

.. code-block:: bash

   bitchute video VIDEO_ID [OPTIONS]

Arguments:

``VIDEO_ID``
   Video ID to retrieve (required)

Options:

``--counts``
   Include like/dislike counts

``--media``
   Include media URL information

Examples:

.. code-block:: bash

   # Get basic video info
   bitchute video CLrgZP4RWyly
   
   # Get complete video details
   bitchute video CLrgZP4RWyly --counts --media

channel
~~~~~~~

Get detailed information for a specific channel.

.. code-block:: bash

   bitchute channel CHANNEL_ID [OPTIONS]

Arguments:

``CHANNEL_ID``
   Channel ID to retrieve (required)

Examples:

.. code-block:: bash

   # Get channel information
   bitchute channel channel_id_here
   
   # Export channel data
   bitchute channel channel_id_here --format json

channel-videos
~~~~~~~~~~~~~~

Get videos from a specific channel.

.. code-block:: bash

   bitchute channel-videos CHANNEL_ID [OPTIONS]

Arguments:

``CHANNEL_ID``
   Channel ID (required)

Options:

``--limit, -l INTEGER``
   Number of videos to retrieve (default: 50)

``--order {latest,popular,oldest}``
   Video ordering (default: latest)

Examples:

.. code-block:: bash

   # Get latest videos from channel
   bitchute channel-videos channel_id_here --limit 100
   
   # Get most popular videos from channel
   bitchute channel-videos channel_id_here --order popular --analyze

Output Formats
--------------

The CLI supports multiple output formats specified with ``--format``:

CSV Format
~~~~~~~~~~

.. code-block:: bash

   bitchute trending --format csv

Creates timestamped CSV files with full data.

JSON Format
~~~~~~~~~~~

.. code-block:: bash

   bitchute search "example" --format json

Creates structured JSON files with nested data preserved.

Excel Format
~~~~~~~~~~~~

.. code-block:: bash

   bitchute popular --format xlsx

Creates Excel workbooks with formatted data tables.

Multiple Formats
~~~~~~~~~~~~~~~~

.. code-block:: bash

   bitchute trending --format csv,json,xlsx

Creates all specified formats with consistent naming.

Data Analysis
-------------

Use ``--analyze`` to get comprehensive statistics:

.. code-block:: bash

   bitchute trending --analyze

Output includes:

* Total videos and view statistics
* Engagement metrics and ratios
* Top channels and hashtags
* Duration analysis
* Upload patterns

Examples:

.. code-block:: bash

   # Analyze trending videos
   bitchute trending --timeframe week --limit 200 --analyze
   
   # Analyze search results
   bitchute search "crypto" --limit 500 --analyze --format xlsx

Automation and Scripting
-------------------------

Batch Processing
~~~~~~~~~~~~~~~~

.. code-block:: bash

   #!/bin/bash
   
   # Daily data collection script
   DATE=$(date +%Y%m%d)
   
   # Collect trending data
   bitchute trending --timeframe day --limit 100 --format csv,json
   
   # Collect popular data
   bitchute popular --limit 200 --format csv
   
   # Search for specific topics
   bitchute search "climate" --limit 100 --format json
   bitchute search "technology" --limit 100 --format json

Cron Jobs
~~~~~~~~~

.. code-block:: bash

   # Add to crontab for daily collection at 9 AM
   0 9 * * * /usr/local/bin/bitchute trending --limit 100 --format csv

Exit Codes
----------

The CLI uses standard exit codes:

* ``0`` - Success
* ``1`` - Error (API failure, validation error, etc.)

Use in scripts:

.. code-block:: bash

   if bitchute trending --limit 50; then
       echo "Data collection successful"
   else
       echo "Data collection failed"
       exit 1
   fi

Configuration
-------------

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Set default options via environment variables:

.. code-block:: bash

   export BITCHUTE_DEFAULT_LIMIT=100
   export BITCHUTE_DEFAULT_FORMAT=csv,json
   export BITCHUTE_VERBOSE=true

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**ChromeDriver Errors**

Ensure Chrome and ChromeDriver are installed:

.. code-block:: bash

   # macOS
   brew install --cask google-chrome
   brew install chromedriver

**Permission Errors**

Check file permissions for output directory:

.. code-block:: bash

   chmod 755 ./
   mkdir -p downloads
   chmod 755 downloads

**Network Timeouts**

Increase timeout for slow connections:

.. code-block:: bash

   bitchute trending --timeout 120

Verbose Mode
~~~~~~~~~~~~

Use ``--verbose`` for detailed error information:

.. code-block:: bash

   bitchute search "example" --verbose

This provides:

* Detailed API request information
* Progress indicators
* Error details and stack traces
* Performance metrics

CLI Module Reference
--------------------

.. automodule:: bitchute.cli
   :members:
   :undoc-members:
   :show-inheritance: