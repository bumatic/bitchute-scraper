Core API
========

The :mod:`bitchute.core` module provides the main API client for interacting with the BitChute platform.

BitChuteAPI Class
-----------------

.. autoclass:: bitchute.core.BitChuteAPI
   :members:
   :undoc-members:
   :show-inheritance:

Platform Recommendations
-------------------------

These methods retrieve curated content from BitChute's platform recommendations.

Trending Videos
~~~~~~~~~~~~~~~

.. automethod:: bitchute.core.BitChuteAPI.get_trending_videos

Example:

.. code-block:: python

   # Get today's trending videos
   trending = api.get_trending_videos('day', limit=50)
   
   # Get weekly trending with downloads
   weekly = api.get_trending_videos(
       'week', 
       limit=100,
       include_details=True,
       download_thumbnails=True
   )

Popular Videos
~~~~~~~~~~~~~~

.. automethod:: bitchute.core.BitChuteAPI.get_popular_videos

Example:

.. code-block:: python

   # Get popular videos
   popular = api.get_popular_videos(limit=100)
   
   # Get with full details and downloads
   popular_detailed = api.get_popular_videos(
       limit=50,
       include_details=True,
       download_thumbnails=True,
       download_videos=True
   )

Recent Videos
~~~~~~~~~~~~~

.. automethod:: bitchute.core.BitChuteAPI.get_recent_videos

.. automethod:: bitchute.core.BitChuteAPI.get_all_videos

Example:

.. code-block:: python

   # Get recent uploads
   recent = api.get_recent_videos(limit=100)
   
   # Get