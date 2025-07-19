Data Models
===========

The :mod:`bitchute.models` module provides comprehensive data models for BitChute platform entities with computed properties and download support.

Video Model
-----------

.. autoclass:: bitchute.models.Video
   :members:
   :undoc-members:
   :show-inheritance:

The Video model represents a BitChute video with complete metadata, engagement statistics, and local file paths for downloaded media.

**Key Properties:**

* Core identifiers (id, title, description)
* Engagement metrics (view_count, like_count, dislike_count)
* Channel information (channel_id, channel_name)
* Media URLs and local file paths
* Computed properties for analysis

**Computed Properties:**

.. automethod:: bitchute.models.Video.engagement_rate

.. automethod:: bitchute.models.Video.like_ratio

.. automethod:: bitchute.models.Video.duration_seconds

**Download Properties:**

.. automethod:: bitchute.models.Video.has_local_thumbnail

.. automethod:: bitchute.models.Video.has_local_video

.. automethod:: bitchute.models.Video.is_fully_downloaded

Example:

.. code-block:: python

   # Access video properties
   video = videos.iloc[0]  # From DataFrame
   
   # Basic information
   print(f"Title: {video['title']}")
   print(f"Views: {video['view_count']:,}")
   print(f"Channel: {video['channel_name']}")
   
   # Computed metrics
   engagement = video['engagement_rate']
   like_ratio = video['like_ratio']
   duration_sec = video['duration_seconds']
   
   # Download status
   has_thumb = video['has_local_thumbnail']
   has_video = video['has_local_video']

Channel Model
-------------

.. autoclass:: bitchute.models.Channel
   :members:
   :undoc-members:
   :show-inheritance:

The Channel model represents a BitChute channel with complete metadata, statistics, and configuration settings.

**Key Properties:**

* Core identifiers (id, name, description)
* Statistics (video_count, subscriber_count, view_count)
* Profile information (profile_id, profile_name)
* Display settings and features
* Social media links

**Computed Properties:**

.. automethod:: bitchute.models.Channel.subscriber_count_numeric

.. automethod:: bitchute.models.Channel.average_views_per_video

Example:

.. code-block:: python

   # Access channel properties
   channel = channels.iloc[0]  # From DataFrame
   
   # Basic information
   print(f"Name: {channel['name']}")
   print(f"Videos: {channel['video_count']}")
   print(f"Subscribers: {channel['subscriber_count']}")
   
   # Computed metrics
   numeric_subs = channel['subscriber_count_numeric']
   avg_views = channel['average_views_per_video']
   
   # Settings
   live_enabled = channel['live_stream_enabled']
   verified = channel['is_verified']

Hashtag Model
-------------

.. autoclass:: bitchute.models.Hashtag
   :members:
   :undoc-members:
   :show-inheritance:

The Hashtag model represents a BitChute hashtag with ranking and usage statistics.

**Computed Properties:**

.. automethod:: bitchute.models.Hashtag.clean_name

.. automethod:: bitchute.models.Hashtag.formatted_name

Example:

.. code-block:: python

   # Access hashtag properties
   hashtag = hashtags.iloc[0]  # From DataFrame
   
   # Basic information
   print(f"Name: {hashtag['name']}")
   print(f"Rank: {hashtag['rank']}")
   print(f"Videos: {hashtag['video_count']}")
   
   # Formatted names
   clean = hashtag['clean_name']      # "bitcoin"
   formatted = hashtag['formatted_name']  # "#bitcoin"

Search and Container Models
---------------------------

SearchResult Model
~~~~~~~~~~~~~~~~~~

.. autoclass:: bitchute.models.SearchResult
   :members:
   :undoc-members:
   :show-inheritance:

Container for search operation results including videos and channels with search metadata.

**Properties:**

.. automethod:: bitchute.models.SearchResult.has_results

.. automethod:: bitchute.models.SearchResult.video_count

.. automethod:: bitchute.models.SearchResult.channel_count

Profile Model
~~~~~~~~~~~~~

.. autoclass:: bitchute.models.Profile
   :members:
   :undoc-members:
   :show-inheritance:

Represents a BitChute user profile associated with channels.

Statistics and Monitoring Models
---------------------------------

APIStats Model
~~~~~~~~~~~~~~

.. autoclass:: bitchute.models.APIStats
   :members:
   :undoc-members:
   :show-inheritance:

Tracks API usage patterns, performance metrics, and session statistics.

**Computed Properties:**

.. automethod:: bitchute.models.APIStats.success_rate

.. automethod:: bitchute.models.APIStats.error_rate

.. automethod:: bitchute.models.APIStats.cache_hit_rate

.. automethod:: bitchute.models.APIStats.session_duration

DownloadResult Model
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: bitchute.models.DownloadResult
   :members:
   :undoc-members:
   :show-inheritance:

Represents the result of a media download operation with file information and statistics.

**Properties:**

.. automethod:: bitchute.models.DownloadResult.has_thumbnail

.. automethod:: bitchute.models.DownloadResult.has_video

.. automethod:: bitchute.models.DownloadResult.file_size_formatted

Example Usage Patterns
-----------------------

Working with Video Data
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get videos with engagement analysis
   videos = api.get_trending_videos('day', limit=100, include_details=True)
   
   # Analyze engagement patterns
   high_engagement = videos[videos['engagement_rate'] > 0.05]
   
   # Sort by like ratio
   liked_videos = videos.sort_values('like_ratio', ascending=False)
   
   # Filter by duration
   long_videos = videos[videos['duration_seconds'] > 1800]  # > 30 minutes

Working with Channel Data
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get channels with detailed analysis
   channels = api.search_channels('news', limit=50, include_details=True)
   
   # Sort by subscriber count
   popular_channels = channels.sort_values('subscriber_count_numeric', ascending=False)
   
   # Find most productive channels
   productive = channels.sort_values('average_views_per_video', ascending=False)

Data Conversion Methods
-----------------------

All models provide ``to_dict()`` methods for converting to dictionary format:

.. code-block:: python

   # Convert model instances to dictionaries
   video_dict = video.to_dict()  # Includes computed properties
   channel_dict = channel.to_dict()
   hashtag_dict = hashtag.to_dict()
   
   # Access all properties including computed ones
   print(video_dict['engagement_rate'])
   print(channel_dict['subscriber_count_numeric'])
   print(hashtag_dict['formatted_name'])

Schema Consistency
------------------

All API methods return pandas DataFrames with consistent schemas. The models define the expected columns and data types:

**Video DataFrame Schema:**

* String columns: id, title, description, channel_name, etc.
* Numeric columns: view_count, like_count, dislike_count, duration_seconds
* Boolean columns: is_short, has_local_thumbnail, is_fully_downloaded
* List columns: hashtags, social_links

**Channel DataFrame Schema:**

* String columns: id, name, description, subscriber_count, etc.
* Numeric columns: video_count, view_count, subscriber_count_numeric
* Boolean columns: is_verified, live_stream_enabled, is_subscribed

This consistency ensures that data processing and analysis code works reliably across different API methods.