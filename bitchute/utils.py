"""
BitChute Scraper Utilities Module

Comprehensive utility classes and functions for BitChute data processing,
rate limiting, request building, data export, content filtering, and caching.

This module provides essential supporting functionality for the BitChute API
client including data processors, rate limiters, export utilities, and
analysis tools for efficient data collection and processing workflows.

Classes:
    RateLimiter: Thread-safe rate limiting for API requests
    RequestBuilder: Builds and validates API request payloads
    DataProcessor: Processes and parses API response data
    PaginationHelper: Handles paginated API responses
    BulkProcessor: Processes multiple items concurrently
    DataExporter: Exports data to various file formats
    ContentFilter: Filters and processes content by criteria
    CacheManager: Simple in-memory cache for API responses
"""

import time
import logging
import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import asdict
from datetime import datetime, timezone
import threading
import concurrent.futures

import pandas as pd
from .models import Video, Channel, Hashtag
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe rate limiter for API requests.

    Implements rate limiting to prevent API throttling by enforcing
    minimum intervals between requests in a thread-safe manner.

    Attributes:
        rate_limit: Minimum seconds between requests.
        last_request: Timestamp of last request.

    Example:
        >>> limiter = RateLimiter(rate_limit=0.5)
        >>> limiter.wait()  # Blocks if needed to respect rate limit
        >>> # Make API request here
        >>> limiter.wait()  # May block again
    """

    def __init__(self, rate_limit: float = 0.5):
        """Initialize rate limiter with specified rate.

        Args:
            rate_limit: Minimum seconds between requests.
        """
        self.rate_limit = rate_limit
        self.last_request = 0
        self._lock = threading.Lock()

    def wait(self):
        """Wait if necessary to respect the rate limit.

        Blocks execution until enough time has passed since the last
        request to respect the configured rate limit.

        Thread-safe implementation ensures proper rate limiting across
        multiple concurrent operations.

        Example:
            >>> limiter = RateLimiter(1.0)  # 1 second between requests
            >>> limiter.wait()
            >>> print("First request can proceed")
            >>> limiter.wait()  # Will wait ~1 second
            >>> print("Second request can proceed")
        """
        with self._lock:
            elapsed = time.time() - self.last_request
            if elapsed < self.rate_limit:
                sleep_time = self.rate_limit - elapsed
                time.sleep(sleep_time)
            self.last_request = time.time()


class RequestBuilder:
    """Builds and validates API request payloads.

    Provides static methods to construct properly formatted payloads
    for various BitChute API endpoints with appropriate validation
    and parameter handling.

    Example:
        >>> payload = RequestBuilder.build_video_request(
        ...     selection="trending-day",
        ...     limit=50,
        ...     offset=0
        ... )
        >>> print(payload)
        {'selection': 'trending-day', 'limit': 50, 'offset': 0, 'advertisable': True}
    """

    @staticmethod
    def build_video_request(
        selection: str,
        offset: int = 0,
        limit: int = 20,
        advertisable: bool = True,
        is_short: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Build video request payload for video endpoints.

        Args:
            selection: Video selection type (trending-day, popular, all, etc.).
            offset: Pagination offset for results.
            limit: Maximum number of results to return.
            advertisable: Whether to include advertisable content.
            is_short: Filter for short-form content (None for no filter).

        Returns:
            dict: Formatted request payload for video endpoints.

        Example:
            >>> payload = RequestBuilder.build_video_request(
            ...     "popular", offset=50, limit=25
            ... )
            >>> payload['selection']
            'popular'
        """
        payload = {
            "selection": selection,
            "offset": offset,
            "limit": limit,
            "advertisable": advertisable,
        }

        if is_short is not None:
            payload["is_short"] = is_short

        return payload

    @staticmethod
    def build_search_request(
        query: str,
        offset: int = 0,
        limit: int = 50,
        sensitivity: str = "normal",
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build search request payload for search endpoints.

        Args:
            query: Search query string.
            offset: Pagination offset for results.
            limit: Maximum number of results to return.
            sensitivity: Content sensitivity level (normal, nsfw, nsfl).
            sort: Sort order for results (new, old, views).

        Returns:
            dict: Formatted request payload for search endpoints.

        Example:
            >>> payload = RequestBuilder.build_search_request(
            ...     "bitcoin", limit=100, sort="views"
            ... )
            >>> payload['query']
            'bitcoin'
        """
        payload = {
            "offset": offset,
            "limit": limit,
            "query": query,
            "sensitivity_id": sensitivity,
        }

        if sort:
            payload["sort"] = sort

        return payload

    @staticmethod
    def build_hashtag_request(offset: int = 0, limit: int = 50) -> Dict[str, Any]:
        """Build hashtag request payload for hashtag endpoints.

        Args:
            offset: Pagination offset for results.
            limit: Maximum number of results to return.

        Returns:
            dict: Formatted request payload for hashtag endpoints.

        Example:
            >>> payload = RequestBuilder.build_hashtag_request(limit=100)
            >>> payload['limit']
            100
        """
        return {"offset": offset, "limit": limit}

    @staticmethod
    def build_video_detail_request(video_id: str) -> Dict[str, Any]:
        """Build video detail request payload for individual video data.

        Args:
            video_id: Unique video identifier.

        Returns:
            dict: Formatted request payload for video detail endpoints.

        Example:
            >>> payload = RequestBuilder.build_video_detail_request("abc123")
            >>> payload['video_id']
            'abc123'
        """
        return {"video_id": video_id}


class DataProcessor:
    """Processes and parses API response data with correct field mappings.

    Handles conversion of raw API response data into structured Video,
    Channel, and Hashtag objects with proper field mapping and validation.

    Example:
        >>> processor = DataProcessor()
        >>> video_data = {"video_id": "abc123", "video_name": "Test Video"}
        >>> video = processor.parse_video(video_data)
        >>> video.id
        'abc123'
    """

    def parse_video(self, data: Dict[str, Any], rank: int = 0) -> Video:
        """Parse video data from API response with correct field mapping.

        Converts raw API response data into a structured Video object
        with proper field mapping, type conversion, and validation.

        Args:
            data: Raw video data from API response.
            rank: Video ranking/position in results.

        Returns:
            Video: Parsed Video object with all available fields populated.

        Example:
            >>> processor = DataProcessor()
            >>> raw_data = {
            ...     "video_id": "test123",
            ...     "video_name": "Sample Video",
            ...     "view_count": "1500"
            ... }
            >>> video = processor.parse_video(raw_data)
            >>> video.title
            'Sample Video'
        """
        video = Video()

        try:
            # Core identifiers
            video.id = self._safe_get(data, "video_id", "")
            video.title = self._safe_get(data, "video_name", "")
            video.description = self._safe_get(data, "description", "")

            # View count with safe integer conversion
            video.view_count = self._safe_int(data.get("view_count", 0))

            # Duration and upload information
            video.duration = self._safe_get(data, "duration", "")
            video.upload_date = self._safe_get(data, "date_published", "")

            # Media URLs
            video.thumbnail_url = self._safe_get(data, "thumbnail_url", "")

            # Category mapping - use category_id if available
            video.category_id = self._safe_get(data, "category_id", "")
            video.category = video.category_id or self._safe_get(data, "category", "")

            # Content sensitivity and state
            video.sensitivity = self._safe_get(data, "sensitivity_id", "")
            video.state = self._safe_get(data, "state_id", "")

            # Short-form content detection
            video.is_short = bool(data.get("is_short", data.get("is_shorts", False)))

            # Channel information from nested structure
            channel = data.get("channel", {})
            if isinstance(channel, dict):
                video.channel_id = self._safe_get(channel, "channel_id", "")
                video.channel_name = self._safe_get(channel, "channel_name", "")
            else:
                # Fallback to legacy uploader structure
                uploader = data.get("uploader", {})
                if isinstance(uploader, dict):
                    video.channel_id = self._safe_get(uploader, "id", "")
                    video.channel_name = self._safe_get(uploader, "name", "")

            # Profile information
            video.profile_id = self._safe_get(data, "profile_id", "")

            # Hashtags processing with proper format handling
            hashtags_data = data.get("hashtags", data.get("tags", []))
            if hashtags_data:
                video.hashtags = []
                for tag_item in hashtags_data:
                    if isinstance(tag_item, dict):
                        # New format: {"hashtag_id": "name", "hashtag_count": count}
                        tag_name = tag_item.get("hashtag_id", "")
                        if tag_name:
                            formatted_tag = (
                                f"#{tag_name}"
                                if not tag_name.startswith("#")
                                else tag_name
                            )
                            video.hashtags.append(formatted_tag)
                    elif isinstance(tag_item, str) and tag_item:
                        # Legacy format: direct string
                        formatted_tag = (
                            f"#{tag_item}" if not tag_item.startswith("#") else tag_item
                        )
                        video.hashtags.append(formatted_tag)

            # Engagement metrics (may be populated later)
            video.like_count = self._safe_int(data.get("like_count", 0))
            video.dislike_count = self._safe_int(data.get("dislike_count", 0))

            # User interaction flags
            video.is_liked = bool(data.get("is_liked", False))
            video.is_disliked = bool(data.get("is_disliked", False))
            video.is_discussable = bool(data.get("is_discussable", True))

            # Display settings
            video.show_comments = bool(data.get("show_comments", True))
            video.show_adverts = bool(data.get("show_adverts", True))
            video.show_promo = bool(data.get("show_promo", True))
            video.show_rantrave = bool(data.get("show_rantrave", False))

            # External platform identifiers
            video.rumble_id = self._safe_get(data, "rumble_id", "")

            # Construct video URL if not provided
            if video.id:
                video.video_url = f"https://www.bitchute.com/video/{video.id}/"
            elif data.get("video_url"):
                relative_url = data.get("video_url", "")
                if relative_url.startswith("/"):
                    video.video_url = f"https://www.bitchute.com{relative_url}"
                else:
                    video.video_url = relative_url

            # Media file information
            video.media_url = self._safe_get(data, "media_url", "")
            video.media_type = self._safe_get(data, "media_type", "")

        except Exception as e:
            logger.warning(f"Error parsing video data: {e}")

        return video

    def parse_channel(self, data: Dict[str, Any], rank: int = 0) -> Channel:
        """Parse channel data from API response with social links support.

        Converts raw API response data into a structured Channel object
        with complete metadata and social media information.

        Args:
            data: Raw channel data from API response.
            rank: Channel ranking/position in results.

        Returns:
            Channel: Parsed Channel object with all available fields populated.

        Example:
            >>> processor = DataProcessor()
            >>> raw_data = {
            ...     "channel_id": "test123",
            ...     "channel_name": "Test Channel",
            ...     "video_count": "50"
            ... }
            >>> channel = processor.parse_channel(raw_data)
            >>> channel.name
            'Test Channel'
        """
        channel = Channel()

        try:
            # Core identifiers with fallback handling
            channel.id = self._safe_get(
                data, "channel_id", self._safe_get(data, "id", "")
            )
            channel.name = self._safe_get(
                data,
                "channel_name",
                self._safe_get(data, "name", data.get("title", "")),
            )
            channel.description = self._safe_get(data, "description", "")
            channel.url_slug = self._safe_get(data, "url_slug", "")

            # Statistics with safe conversion
            channel.video_count = self._safe_int(data.get("video_count", 0))
            channel.subscriber_count = str(data.get("subscriber_count", ""))
            channel.view_count = self._safe_int(data.get("view_count", 0))

            # Date information
            channel.created_date = self._safe_get(
                data, "date_created", data.get("created_at", "")
            )
            channel.last_video_published = self._safe_get(
                data, "last_video_published", ""
            )

            # Profile information
            channel.profile_id = self._safe_get(data, "profile_id", "")
            channel.profile_name = self._safe_get(data, "profile_name", "")

            # Handle nested profile object
            profile = data.get("profile", {})
            if isinstance(profile, dict):
                channel.profile_id = channel.profile_id or self._safe_get(
                    profile, "profile_id", ""
                )
                channel.profile_name = channel.profile_name or self._safe_get(
                    profile, "profile_name", ""
                )

            # Category and sensitivity information
            channel.category_id = self._safe_get(data, "category_id", "")
            channel.category = channel.category_id or self._safe_get(
                data, "category", ""
            )
            channel.sensitivity_id = self._safe_get(data, "sensitivity_id", "")
            channel.sensitivity = channel.sensitivity_id or self._safe_get(
                data, "sensitivity", ""
            )

            # State information
            channel.state_id = self._safe_get(data, "state_id", "")
            channel.state = channel.state_id or self._safe_get(data, "state", "")

            # Media URLs
            channel.thumbnail_url = self._safe_get(data, "thumbnail_url", "")

            # Build channel URL
            if channel.id:
                channel.channel_url = f"https://www.bitchute.com/channel/{channel.id}/"
            elif data.get("channel_url"):
                relative_url = data.get("channel_url", "")
                if relative_url.startswith("/"):
                    channel.channel_url = f"https://www.bitchute.com{relative_url}"
                else:
                    channel.channel_url = relative_url

            # Channel settings and features
            channel.membership_level = self._safe_get(
                data, "membership_level", "Default"
            )
            channel.is_verified = bool(data.get("is_verified", False))
            channel.is_subscribed = bool(data.get("is_subscribed", False))
            channel.is_notified = bool(data.get("is_notified", False))

            # Display preferences
            channel.show_adverts = bool(data.get("show_adverts", True))
            channel.show_comments = bool(data.get("show_comments", True))
            channel.show_rantrave = bool(data.get("show_rantrave", True))

            # Platform features
            channel.live_stream_enabled = bool(data.get("live_stream_enabled", False))
            channel.feature_video = data.get("feature_video")

            # Initialize social links (populated later by API)
            channel.social_links = []

        except Exception as e:
            logger.warning(f"Error parsing channel data: {e}")

        return channel

    def parse_hashtag(self, data: Dict[str, Any], rank: int = 0) -> Hashtag:
        """Parse hashtag data from API response.

        Converts raw API response data into a structured Hashtag object
        with ranking and usage statistics.

        Args:
            data: Raw hashtag data from API response.
            rank: Hashtag ranking/position in results.

        Returns:
            Hashtag: Parsed Hashtag object with trend information.

        Example:
            >>> processor = DataProcessor()
            >>> raw_data = {"hashtag_id": "bitcoin", "hashtag_count": 150}
            >>> hashtag = processor.parse_hashtag(raw_data, rank=5)
            >>> hashtag.name
            'bitcoin'
        """
        hashtag = Hashtag()

        try:
            # Handle different hashtag data formats
            if "hashtag_id" in data:
                # New format from video details
                hashtag.name = self._safe_get(data, "hashtag_id", "")
                hashtag.video_count = self._safe_int(data.get("hashtag_count", 0))
            else:
                # Legacy format
                hashtag.name = self._safe_get(data, "name", "")
                hashtag.video_count = self._safe_int(data.get("video_count", 0))

            hashtag.rank = rank

            # Build hashtag URL from name
            if hashtag.name:
                clean_name = hashtag.name.lstrip("#")
                hashtag.url = f"https://www.bitchute.com/hashtag/{clean_name}/"

        except Exception as e:
            logger.warning(f"Error parsing hashtag data: {e}")

        return hashtag

    @staticmethod
    def _safe_get(data: Dict[str, Any], key: str, default: str = "") -> str:
        """Safely get string value from dictionary with fallback.

        Args:
            data: Source dictionary.
            key: Key to retrieve.
            default: Default value if key is missing or None.

        Returns:
            str: String value or default if conversion fails.
        """
        value = data.get(key, default)
        return str(value) if value is not None else default

    @staticmethod
    def _safe_int(value: Any) -> int:
        """Safely convert value to integer with fallback.

        Args:
            value: Value to convert to integer.

        Returns:
            int: Integer value or 0 if conversion fails.
        """
        try:
            if value is None:
                return 0
            return int(float(str(value)))
        except (ValueError, TypeError):
            return 0


class PaginationHelper:
    """Helper for handling paginated API responses.

    Provides utilities for fetching multiple pages of data from
    paginated API endpoints with automatic handling of offsets
    and page limits.

    Example:
        >>> helper = PaginationHelper()
        >>> df = helper.get_multiple_pages(
        ...     api.get_trending_videos,
        ...     max_pages=5,
        ...     per_page=50,
        ...     timeframe='day'
        ... )
    """

    @staticmethod
    def get_multiple_pages(
        api_method, max_pages: int = 5, per_page: int = 50, **kwargs
    ) -> pd.DataFrame:
        """Get multiple pages of data from a paginated API method.

        Automatically handles pagination by calling the API method multiple
        times with appropriate offsets and combining results into a single
        DataFrame.

        Args:
            api_method: API method to call for each page.
            max_pages: Maximum number of pages to fetch.
            per_page: Number of items per page request.
            **kwargs: Additional arguments to pass to the API method.

        Returns:
            pd.DataFrame: Combined results from all pages.

        Example:
            >>> # Get 5 pages of trending videos (250 total)
            >>> df = PaginationHelper.get_multiple_pages(
            ...     api.get_trending_videos,
            ...     max_pages=5,
            ...     per_page=50,
            ...     timeframe='day'
            ... )
            >>> len(df)  # Up to 250 videos
        """
        all_data = []

        for page in range(max_pages):
            offset = page * per_page

            try:
                # Call API method with pagination parameters
                if "limit" in api_method.__code__.co_varnames:
                    df = api_method(limit=per_page, offset=offset, **kwargs)
                else:
                    df = api_method(limit=per_page, **kwargs)

                if df.empty:
                    logger.info(
                        f"Page {page + 1}: No data returned, stopping pagination"
                    )
                    break

                all_data.append(df)
                logger.info(f"Page {page + 1}: {len(df)} items")

                # Check if we got fewer items than requested (end of data)
                if len(df) < per_page:
                    logger.info(
                        f"Got {len(df)} items, expected {per_page}. End of data reached."
                    )
                    break

                # Small delay between requests
                time.sleep(0.5)

            except Exception as e:
                logger.warning(f"Failed to get page {page + 1}: {e}")
                break

        if all_data:
            return pd.concat(all_data, ignore_index=True)

        return pd.DataFrame()


class BulkProcessor:
    """Process multiple items concurrently for improved performance.

    Provides utilities for concurrent processing of multiple API requests
    to improve performance when fetching details for large numbers of items.

    Example:
        >>> processor = BulkProcessor()
        >>> video_ids = ['abc123', 'def456', 'ghi789']
        >>> videos = processor.process_video_details(
        ...     api_client, video_ids, max_workers=5
        ... )
    """

    @staticmethod
    def process_video_details(
        api_client,
        video_ids: List[str],
        max_workers: int = 5,
        include_counts: bool = True,
        include_media: bool = False,
    ) -> List[Video]:
        """Get details for multiple videos concurrently.

        Fetches video details for multiple videos using concurrent processing
        to improve performance over sequential requests.

        Note: This is the external API method. Internal functions use the
        unified _fetch_details_parallel() method.

        Args:
            api_client: BitChute API client instance.
            video_ids: List of video IDs to process.
            max_workers: Maximum concurrent workers.
            include_counts: Whether to include like/dislike counts.
            include_media: Whether to include media URLs.

        Returns:
            List[Video]: List of Video objects with details.

        Example:
            >>> api = BitChuteAPI()
            >>> processor = BulkProcessor()
            >>> video_ids = ['abc123', 'def456']
            >>> videos = processor.process_video_details(
            ...     api, video_ids, max_workers=3
            ... )
            >>> len(videos)  # Number of successfully processed videos
        """
        videos = []

        def get_video_details_thread(video_id):
            try:
                return api_client.get_video_details(
                    video_id, include_counts=include_counts, include_media=include_media
                )
            except Exception as e:
                logger.warning(f"Failed to get details for {video_id}: {e}")
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {
                executor.submit(get_video_details_thread, vid): vid for vid in video_ids
            }

            for future in concurrent.futures.as_completed(future_to_id):
                video = future.result()
                if video:
                    videos.append(video)

        logger.info(f"Retrieved details for {len(videos)}/{len(video_ids)} videos")
        return videos


class DataExporter:
    """Export data to various file formats.

    Provides utilities for exporting DataFrame data to multiple formats
    including CSV, JSON, Excel, and Parquet with automatic timestamping
    and error handling.

    Example:
        >>> exporter = DataExporter()
        >>> exported = exporter.export_data(
        ...     df, 'trending_videos', ['csv', 'json', 'xlsx']
        ... )
        >>> print(exported)  # Dict of format -> filepath
    """

    @staticmethod
    def export_data(
        df: pd.DataFrame, filename: str, formats: List[str] = None
    ) -> Dict[str, str]:
        """Export DataFrame to various file formats.

        Exports the provided DataFrame to one or more file formats with
        automatic timestamping and comprehensive error handling.

        Args:
            df: DataFrame to export.
            filename: Base filename without extension.
            formats: List of format strings ('csv', 'json', 'xlsx', 'parquet').
                Defaults to ['csv'] if not specified.

        Returns:
            Dict[str, str]: Dictionary mapping format names to file paths.

        Raises:
            Exception: If export operation fails for any format.

        Example:
            >>> exporter = DataExporter()
            >>> df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
            >>> result = exporter.export_data(df, 'test_data', ['csv', 'json'])
            >>> 'csv' in result  # True
            >>> 'json' in result  # True
        """
        if formats is None:
            formats = ["csv"]

        exported = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for fmt in formats:
            try:
                filepath = f"{filename}_{timestamp}.{fmt}"

                if fmt == "csv":
                    df.to_csv(filepath, index=False, encoding="utf-8")

                elif fmt == "json":
                    df.to_json(filepath, orient="records", indent=2, force_ascii=False)

                elif fmt == "xlsx":
                    df.to_excel(filepath, index=False, engine="openpyxl")

                elif fmt == "parquet":
                    df.to_parquet(filepath, index=False)

                else:
                    logger.warning(f"Unsupported format: {fmt}")
                    continue

                exported[fmt] = filepath
                logger.info(f"Exported to {filepath}")

            except Exception as e:
                logger.error(f"Export failed for {fmt}: {e}")

        return exported


class ContentFilter:
    """Filter and process content based on various criteria.

    Provides comprehensive filtering capabilities for video and channel
    data based on metrics like view count, duration, keywords, and dates.

    Example:
        >>> filter = ContentFilter()
        >>> filtered = filter.filter_by_views(df, min_views=1000, max_views=50000)
        >>> popular = filter.filter_by_keywords(df, ['bitcoin', 'crypto'])
    """

    @staticmethod
    def filter_by_views(
        df: pd.DataFrame, min_views: int = 0, max_views: int = None
    ) -> pd.DataFrame:
        """Filter videos by view count range.

        Args:
            df: DataFrame containing video data.
            min_views: Minimum view count threshold.
            max_views: Maximum view count threshold (None for no limit).

        Returns:
            pd.DataFrame: Filtered DataFrame with videos in view count range.

        Example:
            >>> # Get videos with 1K-10K views
            >>> filtered = ContentFilter.filter_by_views(
            ...     df, min_views=1000, max_views=10000
            ... )
        """
        if df.empty or "view_count" not in df.columns:
            return df

        filtered = df[df["view_count"] >= min_views]

        if max_views is not None:
            filtered = filtered[filtered["view_count"] <= max_views]

        return filtered

    @staticmethod
    def filter_by_duration(
        df: pd.DataFrame, min_seconds: int = 0, max_seconds: int = None
    ) -> pd.DataFrame:
        """Filter videos by duration range.

        Args:
            df: DataFrame containing video data.
            min_seconds: Minimum duration in seconds.
            max_seconds: Maximum duration in seconds (None for no limit).

        Returns:
            pd.DataFrame: Filtered DataFrame with videos in duration range.

        Example:
            >>> # Get videos between 5-15 minutes
            >>> filtered = ContentFilter.filter_by_duration(
            ...     df, min_seconds=300, max_seconds=900
            ... )
        """
        if df.empty or "duration" not in df.columns:
            return df

        def duration_to_seconds(duration_str):
            try:
                return ContentFilter._parse_duration(duration_str)
            except:
                return 0

        df_copy = df.copy()
        df_copy["duration_seconds"] = df_copy["duration"].apply(duration_to_seconds)

        filtered = df_copy[df_copy["duration_seconds"] >= min_seconds]

        if max_seconds is not None:
            filtered = filtered[filtered["duration_seconds"] <= max_seconds]

        # Remove the temporary column
        return filtered.drop("duration_seconds", axis=1)

    @staticmethod
    def filter_by_keywords(
        df: pd.DataFrame, keywords: List[str], column: str = "title"
    ) -> pd.DataFrame:
        """Filter content by keywords in specified column.

        Args:
            df: DataFrame containing content data.
            keywords: List of keywords to search for.
            column: Column name to search in (default: 'title').

        Returns:
            pd.DataFrame: Filtered DataFrame with content matching keywords.

        Example:
            >>> # Find videos about cryptocurrency
            >>> crypto_videos = ContentFilter.filter_by_keywords(
            ...     df, ['bitcoin', 'ethereum', 'crypto'], 'title'
            ... )
        """
        if df.empty or column not in df.columns:
            return df

        if not keywords:
            return df

        # Create case-insensitive regex pattern
        pattern = "|".join(re.escape(keyword) for keyword in keywords)

        filtered = df[df[column].str.contains(pattern, case=False, na=False)]
        return filtered

    @staticmethod
    def filter_by_channel(df: pd.DataFrame, channels: List[str]) -> pd.DataFrame:
        """Filter videos by channel names.

        Args:
            df: DataFrame containing video data.
            channels: List of channel names to filter by.

        Returns:
            pd.DataFrame: Filtered DataFrame with videos from specified channels.

        Example:
            >>> # Get videos from specific news channels
            >>> news_videos = ContentFilter.filter_by_channel(
            ...     df, ['BBC News', 'CNN', 'Fox News']
            ... )
        """
        if df.empty or "channel_name" not in df.columns:
            return df

        if not channels:
            return df

        filtered = df[df["channel_name"].isin(channels)]
        return filtered

    @staticmethod
    def filter_by_date_range(
        df: pd.DataFrame,
        start_date: str = None,
        end_date: str = None,
        date_column: str = "upload_date",
    ) -> pd.DataFrame:
        """Filter content by date range.

        Args:
            df: DataFrame containing content data.
            start_date: Start date string (YYYY-MM-DD format).
            end_date: End date string (YYYY-MM-DD format).
            date_column: Column containing date information.

        Returns:
            pd.DataFrame: Filtered DataFrame with content in date range.

        Example:
            >>> # Get videos from last month
            >>> recent = ContentFilter.filter_by_date_range(
            ...     df, start_date='2024-01-01', end_date='2024-01-31'
            ... )
        """
        if df.empty or date_column not in df.columns:
            return df

        # Convert date column to datetime
        try:
            df_copy = df.copy()
            df_copy[date_column] = pd.to_datetime(df_copy[date_column], errors="coerce")

            if start_date:
                start_dt = pd.to_datetime(start_date)
                df_copy = df_copy[df_copy[date_column] >= start_dt]

            if end_date:
                end_dt = pd.to_datetime(end_date)
                df_copy = df_copy[df_copy[date_column] <= end_dt]

            return df_copy

        except Exception as e:
            logger.warning(f"Date filtering failed: {e}")
            return df

    @staticmethod
    def _parse_duration(duration_str: str) -> int:
        """Parse duration string to seconds.

        Converts duration strings in MM:SS or HH:MM:SS format to total seconds.

        Args:
            duration_str: Duration string (e.g., '12:34' or '1:23:45').

        Returns:
            int: Total duration in seconds.

        Raises:
            ValueError: If duration format is invalid.
        """
        if not duration_str or not isinstance(duration_str, str):
            return 0

        parts = duration_str.strip().split(":")
        if len(parts) == 2:  # MM:SS format
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:  # HH:MM:SS format
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        else:
            return 0


class CacheManager:
    """Simple in-memory cache for API responses.

    Provides thread-safe caching functionality for API responses with
    automatic expiration and size management to improve performance
    and reduce API calls.

    Attributes:
        max_size: Maximum number of cached items.
        ttl: Time to live in seconds for cached items.

    Example:
        >>> cache = CacheManager(max_size=1000, ttl=3600)
        >>> cache.set('key1', 'value1')
        >>> value = cache.get('key1')  # Returns 'value1'
        >>> cache.clear()  # Clear all cached items
    """

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """Initialize cache manager with size and expiration settings.

        Args:
            max_size: Maximum number of cached items.
            ttl: Time to live in seconds for cached items.
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache = {}
        self._timestamps = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        """Get item from cache if it exists and hasn't expired.

        Args:
            key: Cache key to retrieve.

        Returns:
            Any: Cached value or None if not found or expired.

        Example:
            >>> cache = CacheManager()
            >>> cache.set('user_data', {'name': 'John'})
            >>> data = cache.get('user_data')
            >>> print(data)  # {'name': 'John'}
        """
        with self._lock:
            if key not in self._cache:
                return None

            # Check if expired
            if time.time() - self._timestamps[key] > self.ttl:
                del self._cache[key]
                del self._timestamps[key]
                return None

            return self._cache[key]

    def set(self, key: str, value: Any):
        """Set item in cache with automatic size management.

        Args:
            key: Cache key to store under.
            value: Value to cache.

        Example:
            >>> cache = CacheManager()
            >>> cache.set('api_response', {'videos': [...]})
            >>> cache.set('user_preferences', {'theme': 'dark'})
        """
        with self._lock:
            # Remove oldest items if cache is full
            if len(self._cache) >= self.max_size:
                oldest_key = min(
                    self._timestamps.keys(), key=lambda k: self._timestamps[k]
                )
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]

            self._cache[key] = value
            self._timestamps[key] = time.time()

    def clear(self):
        """Clear all cached items.

        Example:
            >>> cache = CacheManager()
            >>> cache.set('key1', 'value1')
            >>> cache.clear()
            >>> cache.get('key1')  # Returns None
        """
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def size(self) -> int:
        """Get current number of cached items.

        Returns:
            int: Number of items currently in cache.

        Example:
            >>> cache = CacheManager()
            >>> cache.set('key1', 'value1')
            >>> cache.set('key2', 'value2')
            >>> cache.size()  # Returns 2
        """
        return len(self._cache)


class DataAnalyzer:
    """Analyze video and channel data with comprehensive statistics.

    Provides advanced analysis capabilities for BitChute data including
    view statistics, engagement metrics, channel analysis, and trend
    identification.

    Example:
        >>> analyzer = DataAnalyzer()
        >>> analysis = analyzer.analyze_videos(videos_df)
        >>> print(f"Average views: {analysis['views']['average']}")
    """

    def analyze_videos(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Perform comprehensive analysis of video data.

        Analyzes video DataFrame to extract statistics about views,
        engagement, duration, channels, and hashtags.

        Args:
            df: DataFrame containing video data.

        Returns:
            Dict[str, Any]: Comprehensive analysis results including:
                - total_videos: Total number of videos analyzed
                - views: View count statistics (total, average, median, range)
                - engagement: Engagement metrics (like ratio, engagement rate)
                - duration: Duration statistics and distribution
                - top_channels: Most active channels by video count
                - top_hashtags: Most popular hashtags
                - upload_patterns: Upload timing analysis

        Example:
            >>> analyzer = DataAnalyzer()
            >>> videos_df = api.get_trending_videos('day', limit=100)
            >>> analysis = analyzer.analyze_videos(videos_df)
            >>> print(f"Total views: {analysis['views']['total']:,}")
            >>> print(f"Top channel: {list(analysis['top_channels'].keys())[0]}")
        """
        if df.empty:
            return {"error": "No data to analyze"}

        analysis = {
            "total_videos": len(df),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # View count analysis
            if "view_count" in df.columns:
                view_counts = df["view_count"].dropna()
                if not view_counts.empty:
                    analysis["views"] = {
                        "total": int(view_counts.sum()),
                        "average": float(view_counts.mean()),
                        "median": float(view_counts.median()),
                        "min": int(view_counts.min()),
                        "max": int(view_counts.max()),
                        "std_dev": float(view_counts.std()),
                    }

            # Engagement analysis
            if "like_count" in df.columns and "dislike_count" in df.columns:
                likes = df["like_count"].fillna(0)
                dislikes = df["dislike_count"].fillna(0)
                total_reactions = likes + dislikes

                if total_reactions.sum() > 0:
                    analysis["engagement"] = {
                        "total_likes": int(likes.sum()),
                        "total_dislikes": int(dislikes.sum()),
                        "like_ratio": float(likes.sum() / total_reactions.sum()),
                        "videos_with_reactions": int((total_reactions > 0).sum()),
                    }

            # Duration analysis
            if "duration" in df.columns:
                durations = []
                for duration_str in df["duration"].dropna():
                    try:
                        seconds = ContentFilter._parse_duration(str(duration_str))
                        if seconds > 0:
                            durations.append(seconds)
                    except:
                        continue

                if durations:
                    durations = pd.Series(durations)
                    analysis["duration"] = {
                        "average_seconds": float(durations.mean()),
                        "average_minutes": float(durations.mean() / 60),
                        "median_seconds": float(durations.median()),
                        "total_hours": float(durations.sum() / 3600),
                        "short_videos": int((durations <= 60).sum()),  # <= 1 minute
                        "long_videos": int((durations >= 1800).sum()),  # >= 30 minutes
                    }

            # Channel analysis
            if "channel_name" in df.columns:
                channel_counts = df["channel_name"].value_counts().head(20)
                analysis["top_channels"] = channel_counts.to_dict()
                analysis["unique_channels"] = int(df["channel_name"].nunique())

            # Hashtag analysis
            if "hashtags" in df.columns:
                all_hashtags = []
                for hashtag_list in df["hashtags"].dropna():
                    if isinstance(hashtag_list, list):
                        all_hashtags.extend(hashtag_list)

                if all_hashtags:
                    hashtag_counts = pd.Series(all_hashtags).value_counts().head(20)
                    analysis["top_hashtags"] = hashtag_counts.to_dict()
                    analysis["unique_hashtags"] = len(set(all_hashtags))

            # Upload pattern analysis
            if "upload_date" in df.columns:
                try:
                    upload_dates = pd.to_datetime(
                        df["upload_date"], errors="coerce"
                    ).dropna()
                    if not upload_dates.empty:
                        analysis["upload_patterns"] = {
                            "date_range": {
                                "earliest": upload_dates.min().isoformat(),
                                "latest": upload_dates.max().isoformat(),
                            },
                            "uploads_by_hour": upload_dates.dt.hour.value_counts().to_dict(),
                            "uploads_by_day": upload_dates.dt.day_name()
                            .value_counts()
                            .to_dict(),
                        }
                except Exception as e:
                    logger.warning(f"Upload pattern analysis failed: {e}")

            # Category analysis
            if "category" in df.columns:
                category_counts = df["category"].value_counts().head(10)
                analysis["top_categories"] = category_counts.to_dict()

            # Short-form content analysis
            if "is_short" in df.columns:
                short_count = df["is_short"].sum()
                analysis["content_types"] = {
                    "short_videos": int(short_count),
                    "regular_videos": int(len(df) - short_count),
                    "short_percentage": float(short_count / len(df) * 100),
                }

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            analysis["error"] = str(e)

        return analysis

    def analyze_channels(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Perform comprehensive analysis of channel data.

        Args:
            df: DataFrame containing channel data.

        Returns:
            Dict[str, Any]: Channel analysis results including subscriber
                distributions, video count statistics, and activity patterns.
        """
        if df.empty:
            return {"error": "No channel data to analyze"}

        analysis = {
            "total_channels": len(df),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Video count analysis
            if "video_count" in df.columns:
                video_counts = df["video_count"].dropna()
                if not video_counts.empty:
                    analysis["video_statistics"] = {
                        "total_videos": int(video_counts.sum()),
                        "average_per_channel": float(video_counts.mean()),
                        "median_per_channel": float(video_counts.median()),
                        "most_prolific": int(video_counts.max()),
                    }

            # Subscriber analysis
            if "subscriber_count" in df.columns:
                # Convert formatted subscriber counts to numeric
                numeric_subs = []
                for sub_count in df["subscriber_count"].dropna():
                    try:
                        if "K" in str(sub_count).upper():
                            numeric_subs.append(
                                int(
                                    float(str(sub_count).upper().replace("K", ""))
                                    * 1000
                                )
                            )
                        elif "M" in str(sub_count).upper():
                            numeric_subs.append(
                                int(
                                    float(str(sub_count).upper().replace("M", ""))
                                    * 1000000
                                )
                            )
                        else:
                            numeric_subs.append(int(float(str(sub_count))))
                    except:
                        continue

                if numeric_subs:
                    subs_series = pd.Series(numeric_subs)
                    analysis["subscriber_statistics"] = {
                        "total_subscribers": int(subs_series.sum()),
                        "average_per_channel": float(subs_series.mean()),
                        "median_per_channel": float(subs_series.median()),
                        "largest_channel": int(subs_series.max()),
                    }

        except Exception as e:
            logger.error(f"Channel analysis error: {e}")
            analysis["error"] = str(e)

        return analysis
