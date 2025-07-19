BitChute Scraper Documentation
================================

Welcome to BitChute Scraper's documentation! This package provides a modern, high-performance Python interface for scraping BitChute platform data using official API endpoints.

**Features:**

* Fast API-based data collection (10x faster than HTML parsing)
* Automatic media downloads with smart caching
* Comprehensive data models with computed properties
* Concurrent processing with configurable rate limiting
* Multiple export formats (CSV, JSON, Excel, Parquet)
* Command-line interface for easy automation
* Robust error handling with automatic retries

Quick Start
-----------

Install the package:

.. code-block:: bash

   pip install bitchute-scraper

Basic usage:

.. code-block:: python

   import bitchute
   
   # Initialize API client
   api = bitchute.BitChuteAPI(verbose=True)
   
   # Get trending videos
   trending = api.get_trending_videos('day', limit=50)
   print(f"Retrieved {len(trending)} trending videos")

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   
   installation
   quickstart
   cli

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   
   api/core
   api/models

API Overview
------------

The package is organized into several key modules:

:mod:`bitchute.core`
   Main API client with all data collection methods

:mod:`bitchute.models`
   Data models for videos, channels, and hashtags

:mod:`bitchute.utils`
   Utility classes for data processing and export

:mod:`bitchute.download_manager`
   Media download functionality with concurrent processing

:mod:`bitchute.cli`
   Command-line interface for automation

Core Methods
~~~~~~~~~~~~

**Platform Recommendations:**

* :meth:`~bitchute.core.BitChuteAPI.get_trending_videos` - Trending videos by timeframe
* :meth:`~bitchute.core.BitChuteAPI.get_popular_videos` - Popular videos
* :meth:`~bitchute.core.BitChuteAPI.get_recent_videos` - Most recent uploads

**Search Functions:**

* :meth:`~bitchute.core.BitChuteAPI.search_videos` - Video search with filters
* :meth:`~bitchute.core.BitChuteAPI.search_channels` - Channel search

**Individual Items:**

* :meth:`~bitchute.core.BitChuteAPI.get_video_info` - Single video details
* :meth:`~bitchute.core.BitChuteAPI.get_channel_info` - Channel information

Indices and Tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`