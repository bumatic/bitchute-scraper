"""
BitChute Scraper Core API Client

This module provides the main BitChuteAPI class for interacting with the BitChute platform.
"""

import time
import logging
import re
from typing import Dict, List, Optional, Union, Any
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd
from retrying import retry

from .exceptions import (
    BitChuteAPIError,
    TokenExtractionError,
    RateLimitError,
    ValidationError,
)
from .models import Video, Channel, Hashtag
from .token_manager import TokenManager
from .utils import DataProcessor, RateLimiter, RequestBuilder
from .validators import InputValidator
from .download_manager import MediaDownloadManager

logger = logging.getLogger(__name__)


class SensitivityLevel(Enum):
    """Content sensitivity levels for search results."""

    NORMAL = "normal"
    NSFW = "nsfw"
    NSFL = "nsfl"


class SortOrder(Enum):
    """Video sort orders for search results."""

    NEW = "new"
    OLD = "old"
    VIEWS = "views"


class VideoSelection(Enum):
    """Video selection types for trending videos."""

    TRENDING_DAY = "trending-day"
    TRENDING_WEEK = "trending-week"
    TRENDING_MONTH = "trending-month"
    POPULAR = "popular"
    ALL = "all"


class BitChuteAPI:
    """
    BitChute API client for scraping video, channel, and platform data.

    This client provides methods to access BitChute's video listings, search functionality,
    and individual video/channel details. It supports automatic downloading of thumbnails
    and videos when enabled.

    Args:
        verbose: Enable verbose logging output.
        cache_tokens: Cache authentication tokens to disk.
        rate_limit: Minimum seconds between API requests.
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts for failed requests.
        max_workers: Maximum concurrent workers for parallel operations.
        enable_downloads: Enable automatic media downloads.
        download_base_dir: Base directory for downloads.
        thumbnail_folder: Subdirectory for thumbnails.
        video_folder: Subdirectory for videos.
        force_redownload: Force redownload of existing files.
        max_concurrent_downloads: Maximum concurrent downloads.

    Example:
        >>> api = BitChuteAPI(verbose=True)
        >>> trending = api.get_trending_videos('day', limit=10)
        >>> print(f"Found {len(trending)} trending videos")
    """

    def __init__(
        self,
        verbose: bool = False,
        cache_tokens: bool = True,
        rate_limit: float = 0.5,
        timeout: int = 30,
        max_retries: int = 3,
        max_workers: int = 8,
        enable_downloads: bool = False,
        download_base_dir: str = "media",
        thumbnail_folder: str = "thumbnails",
        video_folder: str = "videos",
        force_redownload: bool = False,
        max_concurrent_downloads: int = 3,
    ):
        """Initialize BitChute API client with configuration options."""
        self.verbose = verbose
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_workers = max_workers
        self.enable_downloads = enable_downloads

        self._setup_logging()

        # Initialize core components
        self.token_manager = TokenManager(cache_tokens, verbose)
        self.rate_limiter = RateLimiter(rate_limit)
        self.request_builder = RequestBuilder()
        self.data_processor = DataProcessor()
        self.validator = InputValidator()

        # Initialize download manager if enabled
        if self.enable_downloads:
            self.download_manager = MediaDownloadManager(
                base_dir=download_base_dir,
                thumbnail_folder=thumbnail_folder,
                video_folder=video_folder,
                force_redownload=force_redownload,
                max_concurrent_downloads=max_concurrent_downloads,
                timeout=timeout,
                verbose=verbose,
            )

            if self.verbose:
                logger.info(f"Downloads enabled - saving to: {download_base_dir}")
        else:
            self.download_manager = None

        self.base_url = "https://api.bitchute.com/api"
        self.session = self._create_session()

        # Statistics tracking
        self.stats = {
            "requests_made": 0,
            "cache_hits": 0,
            "errors": 0,
            "last_request_time": 0,
            "session_start_time": time.time(),
        }

    def _setup_logging(self):
        """Configure logging based on verbosity setting."""
        level = logging.INFO if self.verbose else logging.WARNING
        logging.basicConfig(
            level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        if not self.verbose:
            for logger_name in ["selenium", "urllib3", "WDM"]:
                logging.getLogger(logger_name).setLevel(logging.WARNING)

    def _create_session(self) -> requests.Session:
        """Create optimized requests session with retry configuration."""
        session = requests.Session()

        session.headers.update(
            {
                "accept": "application/json, text/plain, */*",
                "accept-language": "en-US,en;q=0.9",
                "content-type": "application/json",
                "origin": "https://www.bitchute.com",
                "referer": "https://www.bitchute.com/",
                "user-agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                ),
            }
        )

        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000)
    def _make_request(
        self, endpoint: str, payload: Dict[str, Any], require_token: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Make authenticated API request with error handling and retries.

        Args:
            endpoint: API endpoint path.
            payload: Request payload data.
            require_token: Whether authentication token is required.

        Returns:
            Response data as dictionary, or None if request failed.

        Raises:
            BitChuteAPIError: When API request fails.
            RateLimitError: When rate limit is exceeded.
            ValidationError: When input validation fails.
        """
        self.validator.validate_endpoint(endpoint)
        self.validator.validate_payload(payload)

        self.rate_limiter.wait()

        if require_token:
            token = self.token_manager.get_token()
            if token:
                self.session.headers["x-service-info"] = token
            elif self.verbose:
                logger.warning(f"No token available for {endpoint}")

        url = f"{self.base_url}/{endpoint}"

        try:
            if self.verbose:
                logger.info(f"API Request: {endpoint}")

            response = self.session.post(url, json=payload, timeout=self.timeout)

            self.stats["requests_made"] += 1
            self.stats["last_request_time"] = time.time()

            if response.status_code == 200:
                return response.json()

            elif response.status_code == 429:
                self.stats["errors"] += 1
                raise RateLimitError("Rate limit exceeded")

            elif response.status_code in [401, 403] and require_token:
                logger.info("Token invalid, attempting refresh")
                self.token_manager.invalidate_token()
                token = self.token_manager.get_token()

                if token:
                    self.session.headers["x-service-info"] = token
                    response = self.session.post(
                        url, json=payload, timeout=self.timeout
                    )
                    if response.status_code == 200:
                        return response.json()

            self.stats["errors"] += 1
            error_msg = f"API error: {endpoint} - {response.status_code}"

            if self.verbose:
                logger.warning(f"{error_msg}: {response.text[:200]}")

            raise BitChuteAPIError(error_msg, response.status_code)

        except RateLimitError:
            raise
        except requests.exceptions.RequestException as e:
            self.stats["requests_made"] += 1
            self.stats["errors"] += 1
            self.stats["last_request_time"] = time.time()

            error_msg = f"Request failed: {endpoint} - {str(e)}"

            if self.verbose:
                logger.error(error_msg)

            raise BitChuteAPIError(error_msg) from e

        except Exception as e:
            if isinstance(e, (BitChuteAPIError, RateLimitError, ValidationError)):
                raise

            self.stats["requests_made"] += 1
            self.stats["errors"] += 1
            self.stats["last_request_time"] = time.time()

            error_msg = f"Unexpected error: {endpoint} - {str(e)}"

            if self.verbose:
                logger.error(error_msg)

            raise BitChuteAPIError(error_msg) from e

    def _fetch_details_parallel(
        self, video_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch video details including counts, media URLs, and hashtags in parallel.

        Args:
            video_ids: List of video IDs to process.

        Returns:
            Dictionary mapping video IDs to their detailed information.
        """
        if not video_ids:
            return {}

        if self.verbose:
            logger.info(
                f"Fetching details for {len(video_ids)} videos with {self.max_workers} workers..."
            )

        start_time = time.time()
        details_map = {}

        for video_id in video_ids:
            details_map[video_id] = {
                "video_id": video_id,
                "like_count": 0,
                "dislike_count": 0,
                "view_count": 0,
                "media_url": "",
                "media_type": "",
                "hashtags": [],
            }

        # Temporarily reduce rate limiting for parallel operations
        original_rate_limit = self.rate_limiter.rate_limit
        self.rate_limiter.rate_limit = 0.02

        try:
            # Batch 1: Fetch counts and hashtags
            if self.verbose:
                logger.info("Batch 1: Fetching counts and hashtags...")

            def fetch_counts_and_hashtags(video_id: str) -> Dict[str, Any]:
                """Fetch counts and hashtags for a single video."""
                try:
                    payload = {"video_id": video_id}
                    result = {"video_id": video_id}

                    # Get counts
                    counts_data = self._make_request("beta/video/counts", payload)
                    if counts_data:
                        result.update(
                            {
                                "like_count": int(
                                    counts_data.get("like_count", 0) or 0
                                ),
                                "dislike_count": int(
                                    counts_data.get("dislike_count", 0) or 0
                                ),
                                "view_count": int(
                                    counts_data.get("view_count", 0) or 0
                                ),
                            }
                        )

                    # Get hashtags from video details
                    video_details = self._make_request(
                        "beta9/video", payload, require_token=False
                    )
                    if video_details and "hashtags" in video_details:
                        hashtags = []
                        for tag in video_details["hashtags"]:
                            if isinstance(tag, str) and tag.strip():
                                formatted_tag = (
                                    f"#{tag}" if not tag.startswith("#") else tag
                                )
                                hashtags.append(formatted_tag)
                        result["hashtags"] = hashtags

                    return result

                except Exception as e:
                    if self.verbose:
                        logger.warning(f"Failed to fetch details for {video_id}: {e}")

                return {"video_id": video_id}

            # Execute counts and hashtags in parallel
            with ThreadPoolExecutor(
                max_workers=min(self.max_workers, len(video_ids))
            ) as executor:
                future_to_id = {
                    executor.submit(fetch_counts_and_hashtags, video_id): video_id
                    for video_id in video_ids
                }

                for future in as_completed(future_to_id):
                    result = future.result()
                    if result and "video_id" in result:
                        video_id = result["video_id"]
                        for key in [
                            "like_count",
                            "dislike_count",
                            "view_count",
                            "hashtags",
                        ]:
                            if key in result:
                                details_map[video_id][key] = result[key]

            # Batch 2: Fetch media URLs
            if self.verbose:
                logger.info("Batch 2: Fetching media URLs...")

            def fetch_media(video_id: str) -> Dict[str, Any]:
                """Fetch media URL for a single video."""
                try:
                    payload = {"video_id": video_id}
                    data = self._make_request("beta/video/media", payload)
                    if data:
                        return {
                            "video_id": video_id,
                            "media_url": data.get("media_url", ""),
                            "media_type": data.get("media_type", ""),
                        }
                except Exception as e:
                    if self.verbose:
                        logger.warning(f"Failed to fetch media for {video_id}: {e}")

                return {"video_id": video_id}

            # Execute media fetching in parallel
            with ThreadPoolExecutor(
                max_workers=min(self.max_workers, len(video_ids))
            ) as executor:
                future_to_id = {
                    executor.submit(fetch_media, video_id): video_id
                    for video_id in video_ids
                }

                for future in as_completed(future_to_id):
                    result = future.result()
                    if result and "video_id" in result:
                        video_id = result["video_id"]
                        for key in ["media_url", "media_type"]:
                            if key in result:
                                details_map[video_id][key] = result[key]

        finally:
            self.rate_limiter.rate_limit = original_rate_limit

        if self.verbose:
            duration = time.time() - start_time
            success_counts = sum(
                1
                for d in details_map.values()
                if d["like_count"] > 0 or d["view_count"] > 0
            )
            success_media = sum(1 for d in details_map.values() if d["media_url"])
            success_hashtags = sum(1 for d in details_map.values() if d["hashtags"])
            logger.info(
                f"Parallel fetch completed in {duration:.2f}s: {success_counts}/{len(video_ids)} counts, {success_media}/{len(video_ids)} media URLs, {success_hashtags}/{len(video_ids)} hashtags"
            )

        return details_map

    def _apply_details_to_videos(
        self, videos: List, details_map: Dict[str, Dict[str, Any]]
    ):
        """
        Apply fetched details including hashtags to Video objects.

        Args:
            videos: List of Video objects to update.
            details_map: Details from _fetch_details_parallel().
        """
        for video in videos:
            if video.id in details_map:
                details = details_map[video.id]

                # Apply counts (update if higher than current)
                if details["like_count"] > 0:
                    video.like_count = details["like_count"]
                if details["dislike_count"] > 0:
                    video.dislike_count = details["dislike_count"]
                if details["view_count"] > video.view_count:
                    video.view_count = details["view_count"]

                # Apply media info
                if details["media_url"]:
                    video.media_url = details["media_url"]
                if details["media_type"]:
                    video.media_type = details["media_type"]

                # Apply hashtags
                if details["hashtags"]:
                    video.hashtags = details["hashtags"]

    def _ensure_consistent_schema(self, df):
        """
        Ensure DataFrame has consistent schema across all video functions.

        Args:
            df: DataFrame to standardize.

        Returns:
            DataFrame with consistent columns and types.
        """
        expected_columns = {
            "id": "",
            "title": "",
            "description": "",
            "view_count": 0,
            "duration": "",
            "thumbnail_url": "",
            "video_url": "",
            "channel_id": "",
            "channel_name": "",
            "category": "",
            "upload_date": "",
            "hashtags": [],
            "is_short": False,
            "like_count": 0,
            "dislike_count": 0,
            "media_url": "",
            "media_type": "",
            "local_thumbnail_path": "",
            "local_video_path": "",
        }

        # Add missing columns with default values
        for col, default_val in expected_columns.items():
            if col not in df.columns:
                df[col] = default_val

        # Ensure correct column order
        df = df.reindex(columns=list(expected_columns.keys()), fill_value="")

        # Convert types
        numeric_cols = ["view_count", "like_count", "dislike_count"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        boolean_cols = ["is_short"]
        for col in boolean_cols:
            df[col] = df[col].astype(bool)

        return df

    def _process_downloads(
        self,
        videos: List[Video],
        download_thumbnails: bool = False,
        download_videos: bool = False,
        force_redownload: Optional[bool] = None,
    ) -> List[Video]:
        """
        Process downloads for a list of videos and update their file paths.

        Args:
            videos: List of Video objects.
            download_thumbnails: Whether to download thumbnails.
            download_videos: Whether to download videos.
            force_redownload: Override the instance force_redownload setting.

        Returns:
            Updated list of Video objects with local file paths.
        """
        if not ((download_thumbnails or download_videos) or self.enable_downloads):
            return videos

        # Initialize download manager on-demand if needed
        if not self.download_manager and (download_thumbnails or download_videos):
            if self.verbose:
                logger.info(
                    "Download manager not initialized but downloads requested. Initializing with defaults."
                )
            self.download_manager = MediaDownloadManager(
                base_dir="downloads",
                thumbnail_folder="thumbnails",
                video_folder="videos",
                force_redownload=False,
                max_concurrent_downloads=3,
                timeout=self.timeout,
                verbose=self.verbose,
            )

        if not download_thumbnails and not download_videos:
            return videos

        # Override force_redownload if specified
        original_force = None
        if force_redownload is not None:
            original_force = self.download_manager.force_redownload
            self.download_manager.force_redownload = force_redownload

        try:
            download_tasks = []

            for video in videos:
                # Add thumbnail download task
                if download_thumbnails and video.thumbnail_url:
                    download_tasks.append(
                        {
                            "url": video.thumbnail_url,
                            "video_id": video.id,
                            "media_type": "thumbnail",
                            "title": video.title,
                        }
                    )

                # Add video download task
                if download_videos and video.media_url:
                    download_tasks.append(
                        {
                            "url": video.media_url,
                            "video_id": video.id,
                            "media_type": "video",
                            "title": video.title,
                        }
                    )

            if download_tasks:
                # Execute downloads
                results = self.download_manager.download_multiple(
                    download_tasks, show_progress=self.verbose
                )

                # Update video objects with local file paths
                for video in videos:
                    if video.id in results:
                        video_results = results[video.id]

                        # Update thumbnail path
                        if download_thumbnails and "thumbnail" in video_results:
                            if video_results["thumbnail"]:
                                video.local_thumbnail_path = video_results["thumbnail"]

                        # Update video path
                        if download_videos and "video" in video_results:
                            if video_results["video"]:
                                video.local_video_path = video_results["video"]

        finally:
            # Restore original force_redownload setting
            if original_force is not None:
                self.download_manager.force_redownload = original_force

        return videos

    def _fetch_channel_details_parallel(
        self, channel_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch detailed channel information and profile links in parallel.

        Args:
            channel_ids: List of channel IDs to enrich.

        Returns:
            Dictionary mapping channel_id to detailed info including social links.
        """
        if not channel_ids:
            return {}

        if self.verbose:
            logger.info(
                f"Fetching detailed info for {len(channel_ids)} channels with {self.max_workers} workers..."
            )

        start_time = time.time()
        details_map = {}

        # Initialize all channel IDs in results
        for channel_id in channel_ids:
            details_map[channel_id] = {
                "channel_id": channel_id,
                "full_details": {},
                "social_links": [],
            }

        # Temporarily reduce rate limiting for parallel operations
        original_rate_limit = self.rate_limiter.rate_limit
        self.rate_limiter.rate_limit = 0.05

        try:
            # Batch 1: Fetch full channel details
            if self.verbose:
                logger.info("Batch 1: Fetching full channel details...")

            def fetch_channel_details(channel_id: str) -> Dict[str, Any]:
                """Fetch full channel details for a single channel."""
                try:
                    payload = {"channel_id": channel_id}
                    data = self._make_request("beta/channel", payload)
                    if data:
                        return {"channel_id": channel_id, "full_details": data}
                except Exception as e:
                    if self.verbose:
                        logger.warning(
                            f"Failed to fetch channel details for {channel_id}: {e}"
                        )

                return {"channel_id": channel_id}

            # Execute channel details in parallel
            with ThreadPoolExecutor(
                max_workers=min(self.max_workers, len(channel_ids))
            ) as executor:
                future_to_id = {
                    executor.submit(fetch_channel_details, channel_id): channel_id
                    for channel_id in channel_ids
                }

                for future in as_completed(future_to_id):
                    result = future.result()
                    if result and "channel_id" in result:
                        channel_id = result["channel_id"]
                        if "full_details" in result:
                            details_map[channel_id]["full_details"] = result[
                                "full_details"
                            ]

            # Batch 2: Fetch profile links for channels that have profile_id
            if self.verbose:
                logger.info("Batch 2: Fetching profile links...")

            def fetch_profile_links(channel_info: Dict[str, Any]) -> Dict[str, Any]:
                """Fetch profile links for a channel."""
                channel_id = channel_info["channel_id"]
                full_details = channel_info["full_details"]

                try:
                    profile_id = full_details.get("profile_id")
                    if profile_id:
                        payload = {"profile_id": profile_id, "offset": 0, "limit": 20}
                        data = self._make_request("beta/profile/links", payload)
                        if data and "links" in data:
                            return {
                                "channel_id": channel_id,
                                "social_links": data["links"],
                            }
                except Exception as e:
                    if self.verbose:
                        logger.warning(
                            f"Failed to fetch profile links for {channel_id}: {e}"
                        )

                return {"channel_id": channel_id, "social_links": []}

            # Prepare channels that have profile_id for link fetching
            channels_with_profiles = []
            for channel_id, details in details_map.items():
                if details["full_details"].get("profile_id"):
                    channels_with_profiles.append(
                        {
                            "channel_id": channel_id,
                            "full_details": details["full_details"],
                        }
                    )

            # Execute profile links in parallel
            if channels_with_profiles:
                with ThreadPoolExecutor(
                    max_workers=min(self.max_workers, len(channels_with_profiles))
                ) as executor:
                    future_to_id = {
                        executor.submit(
                            fetch_profile_links, channel_info
                        ): channel_info["channel_id"]
                        for channel_info in channels_with_profiles
                    }

                    for future in as_completed(future_to_id):
                        result = future.result()
                        if result and "channel_id" in result:
                            channel_id = result["channel_id"]
                            details_map[channel_id]["social_links"] = result[
                                "social_links"
                            ]

        finally:
            # Restore original rate limiting
            self.rate_limiter.rate_limit = original_rate_limit

        # Log results
        if self.verbose:
            duration = time.time() - start_time
            success_details = sum(1 for d in details_map.values() if d["full_details"])
            success_links = sum(1 for d in details_map.values() if d["social_links"])
            logger.info(
                f"Channel details fetch completed in {duration:.2f}s: {success_details}/{len(channel_ids)} details, {success_links}/{len(channel_ids)} social links"
            )

        return details_map

    def _apply_channel_details_to_channels(
        self, channels: List, details_map: Dict[str, Dict[str, Any]]
    ):
        """Apply fetched detailed information to Channel objects.

        Args:
            channels: List of Channel objects to enrich with detailed information.
            details_map: Dictionary mapping channel IDs to their detailed info from
                _fetch_channel_details_parallel().
        """
        for channel in channels:
            if channel.id in details_map:
                details = details_map[channel.id]

                # Apply full channel details
                full_details = details.get("full_details", {})
                if full_details:
                    channel.description = full_details.get(
                        "description", channel.description
                    )
                    channel.video_count = int(
                        full_details.get("video_count", channel.video_count) or 0
                    )
                    channel.view_count = int(
                        full_details.get("view_count", channel.view_count) or 0
                    )
                    channel.subscriber_count = str(
                        full_details.get("subscriber_count", channel.subscriber_count)
                    )
                    channel.created_date = full_details.get(
                        "date_created", channel.created_date
                    )
                    channel.last_video_published = full_details.get(
                        "last_video_published", channel.last_video_published
                    )
                    channel.profile_id = full_details.get(
                        "profile_id", channel.profile_id
                    )
                    channel.profile_name = full_details.get(
                        "profile_name", channel.profile_name
                    )
                    channel.membership_level = full_details.get(
                        "membership_level", channel.membership_level
                    )
                    channel.url_slug = full_details.get("url_slug", channel.url_slug)
                    channel.is_subscribed = bool(
                        full_details.get("is_subscribed", channel.is_subscribed)
                    )
                    channel.is_notified = bool(
                        full_details.get("is_notified", channel.is_notified)
                    )
                    channel.live_stream_enabled = bool(
                        full_details.get(
                            "live_stream_enabled", channel.live_stream_enabled
                        )
                    )
                    channel.feature_video = full_details.get(
                        "feature_video", channel.feature_video
                    )

                # Apply social links
                social_links = details.get("social_links", [])
                channel.social_links = social_links

    def _ensure_consistent_channel_schema(
        self, df: pd.DataFrame, include_details: bool = False
    ):
        """Ensure DataFrame has consistent channel schema across all channel functions.

        Args:
            df: DataFrame to standardize.
            include_details: Whether detailed fields should be included in the schema.

        Returns:
            DataFrame with consistent columns and types.
        """
        # Basic channel columns (always present)
        basic_columns = {
            "id": "",
            "name": "",
            "description": "",
            "url_slug": "",
            "video_count": 0,
            "subscriber_count": "",
            "view_count": 0,
            "created_date": "",
            "last_video_published": "",
            "profile_id": "",
            "profile_name": "",
            "category": "",
            "category_id": "",
            "sensitivity": "",
            "sensitivity_id": "",
            "thumbnail_url": "",
            "channel_url": "",
            "state": "",
            "state_id": "",
            "scrape_timestamp": 0.0,
        }

        # Additional columns when include_details=True
        if include_details:
            detailed_columns = {
                "membership_level": "Default",
                "is_verified": False,
                "is_subscribed": False,
                "is_notified": False,
                "show_adverts": True,
                "show_comments": True,
                "show_rantrave": True,
                "live_stream_enabled": False,
                "feature_video": None,
                "social_links": [],
            }
            basic_columns.update(detailed_columns)

        # Handle empty DataFrame
        if df.empty:
            empty_df = pd.DataFrame(columns=list(basic_columns.keys()))
            return empty_df

        # Add missing columns with default values
        for col, default_val in basic_columns.items():
            if col not in df.columns:
                if isinstance(default_val, list):
                    # For list columns like social_links, create list for each row
                    df[col] = [default_val.copy() for _ in range(len(df))]
                else:
                    # For scalar values, use the default
                    df[col] = default_val

        # Ensure correct column order
        df = df.reindex(columns=list(basic_columns.keys()), fill_value="")

        # Convert types
        numeric_cols = ["video_count", "view_count", "scrape_timestamp"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        if include_details:
            boolean_cols = [
                "is_verified",
                "is_subscribed",
                "is_notified",
                "show_adverts",
                "show_comments",
                "show_rantrave",
                "live_stream_enabled",
            ]
            for col in boolean_cols:
                if col in df.columns:
                    df[col] = df[col].astype(bool)

        return df

    # ================================
    # Get Platform Recommendations
    # ================================

    def get_trending_videos(
        self,
        timeframe: str = "day",
        limit: int = 20,
        include_details: bool = False,
        download_thumbnails: bool = False,
        download_videos: bool = False,
        force_redownload: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Get trending videos from BitChute with optional detail fetching and downloads.

        Args:
            timeframe: Trending period ('day', 'week', or 'month').
            limit: Maximum number of videos to retrieve. Defaults to 20 videos
                shown as trending on the frontend.
            include_details: Whether to fetch like/dislike counts and media URLs.
            download_thumbnails: Whether to download thumbnail images
                (requires enable_downloads=True).
            download_videos: Whether to download video files
                (requires enable_downloads=True).
            force_redownload: Override instance force_redownload setting.

        Returns:
            DataFrame with all requested videos, details, and local file paths.

        Raises:
            ValidationError: If timeframe is invalid or limit is less than 1.
            BitChuteAPIError: If the API request fails.

        Example:
            >>> # Get trending videos for today
            >>> trending = api.get_trending_videos('day', limit=10)
            >>> print(f"Found {len(trending)} trending videos")

            >>> # Get trending videos with downloads
            >>> trending = api.get_trending_videos(
            ...     'week',
            ...     limit=50,
            ...     include_details=True,
            ...     download_thumbnails=True
            ... )
        """
        # Validate inputs
        self.validator.validate_timeframe(timeframe)
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")

        selection_map = {
            "day": VideoSelection.TRENDING_DAY.value,
            "week": VideoSelection.TRENDING_WEEK.value,
            "month": VideoSelection.TRENDING_MONTH.value,
        }

        all_videos = []
        offset = 0
        per_page = 50
        total_retrieved = 0

        if download_videos:
            include_details = True

        while total_retrieved < limit:
            remaining = limit - total_retrieved
            page_limit = min(per_page, remaining)

            payload = {
                "selection": selection_map[timeframe],
                "offset": offset,
                "limit": page_limit,
                "advertisable": True,
            }

            if self.verbose:
                logger.info(
                    f"Fetching trending videos: offset={offset}, limit={page_limit}"
                )

            data = self._make_request("beta/videos", payload)
            if not data or "videos" not in data or not data["videos"]:
                break
            videos = []
            for i, video_data in enumerate(data["videos"], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(video)

                if len(all_videos) + len(videos) >= limit:
                    videos = videos[: limit - len(all_videos)]
                    break

            if videos:
                all_videos.extend(videos)
                total_retrieved = len(all_videos)
                offset += len(videos)

                if self.verbose:
                    logger.info(
                        f"Retrieved {len(videos)} videos (total: {total_retrieved}/{limit})"
                    )

            if total_retrieved >= limit:
                break

            # Check if we got fewer videos than requested (end of data)
            if len(videos) < page_limit:
                break

            if total_retrieved < limit:
                time.sleep(self.rate_limiter.rate_limit)

        # Parallel detail fetching if requested
        if include_details and all_videos:
            video_ids = [video.id for video in all_videos if video.id]
            if video_ids:
                details_map = self._fetch_details_parallel(video_ids)
                self._apply_details_to_videos(all_videos, details_map)

        # Process downloads if requested
        if (download_thumbnails or download_videos) and all_videos:
            all_videos = self._process_downloads(
                all_videos,
                download_thumbnails=download_thumbnails,
                download_videos=download_videos,
                force_redownload=force_redownload,
            )

        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)

            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                download_status = ""
                if download_thumbnails or download_videos:
                    download_parts = []
                    if download_thumbnails:
                        download_parts.append("thumbnails")
                    if download_videos:
                        download_parts.append("videos")
                    download_status = f" and downloaded {'/'.join(download_parts)}"

                logger.info(
                    f"Retrieved {len(df)} trending videos ({timeframe}) {detail_status}{download_status}"
                )

            return df

        return self._ensure_consistent_schema(pd.DataFrame())

    def get_popular_videos(
        self,
        limit: int = 1000,
        include_details: bool = False,
        download_thumbnails: bool = False,
        download_videos: bool = False,
        force_redownload: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Get popular videos from BitChute with optional detail fetching and downloads.

        Args:
            limit: Maximum number of videos to retrieve.
            include_details: Whether to fetch engagement metrics and media URLs.
            download_thumbnails: Whether to download thumbnail images.
            download_videos: Whether to download video files.
            force_redownload: Override instance force_redownload setting.

        Returns:
            DataFrame containing popular videos with consistent schema.

        Raises:
            ValidationError: If limit is less than 1.
            BitChuteAPIError: If the API request fails.

        Example:
            >>> # Get popular videos
            >>> popular = api.get_popular_videos(limit=100)
            >>> print(f"Found {len(popular)} popular videos")

            >>> # Get popular videos with details and downloads
            >>> popular = api.get_popular_videos(
            ...     limit=50,
            ...     include_details=True,
            ...     download_thumbnails=True
            ... )
        """
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")

        all_videos = []
        offset = 0
        per_page = 50

        # Force download details if download videos is True
        if download_videos:
            include_details = True

        while len(all_videos) < limit:
            remaining = limit - len(all_videos)
            page_limit = min(per_page, remaining)

            payload = {
                "selection": VideoSelection.POPULAR.value,
                "offset": offset,
                "limit": page_limit,
                "advertisable": True,
            }

            if self.verbose:
                logger.info(
                    f"Fetching popular videos: offset={offset}, limit={page_limit}"
                )

            data = self._make_request("beta/videos", payload)
            if not data or "videos" not in data or not data["videos"]:
                break

            videos = []
            for i, video_data in enumerate(data["videos"], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(video)

                if len(all_videos) + len(videos) >= limit:
                    break

            if videos:
                all_videos.extend(videos)
                offset += len(videos)

                if len(all_videos) >= limit:
                    all_videos = all_videos[:limit]
                    break

            if len(videos) < page_limit:
                break

            if len(all_videos) < limit:
                time.sleep(self.rate_limiter.rate_limit)

        # Parallel detail fetching if requested
        if include_details and all_videos:
            video_ids = [video.id for video in all_videos if video.id]
            if video_ids:
                details_map = self._fetch_details_parallel(video_ids)
                self._apply_details_to_videos(all_videos, details_map)

        # Process downloads if requested
        if (download_thumbnails or download_videos) and all_videos:
            all_videos = self._process_downloads(
                all_videos,
                download_thumbnails=download_thumbnails,
                download_videos=download_videos,
                force_redownload=force_redownload,
            )

        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)

            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                download_status = ""
                if download_thumbnails or download_videos:
                    download_parts = []
                    if download_thumbnails:
                        download_parts.append("thumbnails")
                    if download_videos:
                        download_parts.append("videos")
                    download_status = f" and downloaded {'/'.join(download_parts)}"

                logger.info(
                    f"Retrieved {len(df)} popular videos {detail_status}{download_status}"
                )
            return df
        return self._ensure_consistent_schema(pd.DataFrame())

    def get_recent_videos(
        self,
        limit: int = 50,
        include_details: bool = False,
        download_thumbnails: bool = False,
        download_videos: bool = False,
        force_redownload: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Get recent videos from BitChute with optional detail fetching and downloads.

        Args:
            limit: Maximum number of videos to retrieve.
            include_details: Whether to fetch engagement metrics and media URLs.
            download_thumbnails: Whether to download thumbnail images.
            download_videos: Whether to download video files.
            force_redownload: Override instance force_redownload setting.

        Returns:
            DataFrame containing recent videos with consistent schema.

        Raises:
            ValidationError: If limit is less than 1.
            BitChuteAPIError: If the API request fails.

        Example:
            >>> # Get recent videos
            >>> recent = api.get_recent_videos(limit=30)
            >>> print(f"Found {len(recent)} recent videos")

            >>> # Get recent videos with details
            >>> recent = api.get_recent_videos(
            ...     limit=100,
            ...     include_details=True
            ... )
        """
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")

        all_videos = []
        offset = 0
        per_page = 50

        # Force download details if download videos is True
        if download_videos:
            include_details = True

        while len(all_videos) < limit:
            remaining = limit - len(all_videos)
            page_limit = min(per_page, remaining)

            payload = {
                "selection": VideoSelection.ALL.value,
                "offset": offset,
                "limit": page_limit,
                "advertisable": True,
            }

            if self.verbose:
                logger.info(
                    f"Fetching recent videos: offset={offset}, limit={page_limit}"
                )

            data = self._make_request("beta/videos", payload)
            if not data or "videos" not in data or not data["videos"]:
                break

            videos = []
            for i, video_data in enumerate(data["videos"], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(video)

                if len(all_videos) + len(videos) >= limit:
                    break

            if videos:
                all_videos.extend(videos)
                offset += len(videos)

                if len(all_videos) >= limit:
                    all_videos = all_videos[:limit]
                    break

            if len(videos) < page_limit:
                break

            if len(all_videos) < limit:
                time.sleep(self.rate_limiter.rate_limit)

        # Parallel detail fetching if requested
        if include_details and all_videos:
            video_ids = [video.id for video in all_videos if video.id]
            if video_ids:
                details_map = self._fetch_details_parallel(video_ids)
                self._apply_details_to_videos(all_videos, details_map)

        # Process downloads if requested
        if (download_thumbnails or download_videos) and all_videos:
            all_videos = self._process_downloads(
                all_videos,
                download_thumbnails=download_thumbnails,
                download_videos=download_videos,
                force_redownload=force_redownload,
            )

        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)

            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                download_status = ""
                if download_thumbnails or download_videos:
                    download_parts = []
                    if download_thumbnails:
                        download_parts.append("thumbnails")
                    if download_videos:
                        download_parts.append("videos")
                    download_status = f" and downloaded {'/'.join(download_parts)}"

                logger.info(
                    f"Retrieved {len(df)} recent videos {detail_status}{download_status}"
                )
            return df

        return self._ensure_consistent_schema(pd.DataFrame())

    def get_all_videos(
        self,
        limit: int = 1000,
        include_details: bool = False,
        download_thumbnails: bool = False,
        download_videos: bool = False,
        force_redownload: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Get all videos (convenience method for getting many recent videos) with optional downloads.

        This is a convenience wrapper around get_recent_videos with higher default limit.

        Args:
            limit: Maximum number of videos to retrieve.
            include_details: Whether to fetch like/dislike counts and media URLs.
            download_thumbnails: Whether to download thumbnail images
                (requires enable_downloads=True).
            download_videos: Whether to download video files
                (requires enable_downloads=True).
            force_redownload: Override instance force_redownload setting.

        Returns:
            DataFrame with all requested videos and consistent schema.

        Example:
            >>> # Get 1000 most recent videos
            >>> df = api.get_all_videos()

            >>> # Get 5000 videos with details and thumbnails
            >>> df = api.get_all_videos(
            ...     limit=5000,
            ...     include_details=True,
            ...     download_thumbnails=True
            ... )
        """
        if self.verbose:
            logger.info(f"Getting all videos (up to {limit})")

        return self.get_recent_videos(
            limit=limit,
            include_details=include_details,
            download_thumbnails=download_thumbnails,
            download_videos=download_videos,
            force_redownload=force_redownload,
        )

    def get_short_videos(
        self,
        limit: int = 1000,
        include_details: bool = False,
        download_thumbnails: bool = False,
        download_videos: bool = False,
        force_redownload: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Get short videos with optional parallel detail fetching and downloads.

        Args:
            limit: Maximum number of videos to retrieve.
            include_details: Whether to fetch like/dislike counts and media URLs.
            download_thumbnails: Whether to download thumbnail images
                (requires enable_downloads=True).
            download_videos: Whether to download video files
                (requires enable_downloads=True).
            force_redownload: Override instance force_redownload setting.

        Returns:
            DataFrame with all requested videos and consistent schema.

        Raises:
            ValidationError: If limit is less than 1.
            BitChuteAPIError: If the API request fails.

        Example:
            >>> # Get short videos
            >>> shorts = api.get_short_videos(limit=50)
            >>> print(f"Found {len(shorts)} short videos")

            >>> # Get short videos with downloads
            >>> shorts = api.get_short_videos(
            ...     limit=100,
            ...     include_details=True,
            ...     download_thumbnails=True
            ... )
        """
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")

        all_videos = []
        offset = 0
        per_page = 50
        total_retrieved = 0

        while total_retrieved < limit:
            remaining = limit - total_retrieved
            page_limit = min(per_page, remaining)

            payload = {
                "selection": VideoSelection.ALL.value,
                "offset": offset,
                "limit": page_limit,
                "advertisable": True,
                "is_short": True,
            }

            if self.verbose:
                logger.info(
                    f"Fetching short videos: offset={offset}, limit={page_limit}"
                )

            data = self._make_request("beta/videos", payload)
            if not data or "videos" not in data or not data["videos"]:
                break

            videos = []
            for i, video_data in enumerate(data["videos"], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(video)

            if videos:
                all_videos.extend(videos)
                total_retrieved += len(videos)
                offset += len(videos)

            if len(videos) < page_limit:
                break

            if total_retrieved < limit:
                time.sleep(self.rate_limiter.rate_limit)

        # Parallel detail fetching if requested
        if include_details and all_videos:
            video_ids = [video.id for video in all_videos if video.id]
            if video_ids:
                details_map = self._fetch_details_parallel(video_ids)
                self._apply_details_to_videos(all_videos, details_map)

        # Process downloads if requested
        if (download_thumbnails or download_videos) and all_videos:
            all_videos = self._process_downloads(
                all_videos,
                download_thumbnails=download_thumbnails,
                download_videos=download_videos,
                force_redownload=force_redownload,
            )

        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)

            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                download_status = ""
                if download_thumbnails or download_videos:
                    download_parts = []
                    if download_thumbnails:
                        download_parts.append("thumbnails")
                    if download_videos:
                        download_parts.append("videos")
                    download_status = f" and downloaded {'/'.join(download_parts)}"

                logger.info(
                    f"Retrieved {len(df)} short videos {detail_status}{download_status}"
                )

            return df

        return self._ensure_consistent_schema(pd.DataFrame())

    def get_member_picked_videos(
        self,
        limit: int = 100,
        include_details: bool = False,
        download_thumbnails: bool = False,
        download_videos: bool = False,
        force_redownload: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Get member-picked videos with optional parallel detail fetching and downloads.

        Args:
            limit: Maximum number of videos to retrieve.
            include_details: Whether to fetch like/dislike counts and media URLs.
            download_thumbnails: Whether to download thumbnail images
                (requires enable_downloads=True).
            download_videos: Whether to download video files
                (requires enable_downloads=True).
            force_redownload: Override instance force_redownload setting.

        Returns:
            DataFrame with member-picked videos and consistent schema.

        Raises:
            ValidationError: If limit is less than 1.
            BitChuteAPIError: If the API request fails.

        Note:
            The date_liked data point is lost due to data structure processing.
            This is a possible future enhancement.

        Example:
            >>> # Get member-picked videos
            >>> picked = api.get_member_picked_videos(limit=50)
            >>> print(f"Found {len(picked)} member-picked videos")

            >>> # Get with details and downloads
            >>> picked = api.get_member_picked_videos(
            ...     limit=100,
            ...     include_details=True,
            ...     download_thumbnails=True
            ... )
        """
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")

        all_videos = []
        offset = 0
        per_page = 50
        total_retrieved = 0

        # Force download details if download videos is True
        if download_videos:
            include_details = True

        while total_retrieved < limit:
            remaining = limit - total_retrieved
            page_limit = min(per_page, remaining)

            payload = {"offset": offset, "limit": page_limit}

            if self.verbose:
                logger.info(
                    f"Fetching member picked videos: offset={offset}, limit={page_limit}"
                )

            data = self._make_request("beta/member_liked_videos", payload)
            if not data or "videos" not in data or not data["videos"]:
                if self.verbose:
                    logger.warning(
                        "No data returned from member picked videos endpoint"
                    )
                break

            # Process data to fit default data structure
            data["videos"] = [v["video"] for v in data["videos"]]

            videos = []
            for i, video_data in enumerate(data["videos"], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(video)

                if len(all_videos) + len(videos) >= limit:
                    videos = videos[: limit - len(all_videos)]
                    break

            if videos:
                all_videos.extend(videos)
                total_retrieved = len(all_videos)
                offset += len(videos)

                if self.verbose:
                    logger.info(
                        f"Retrieved {len(videos)} videos (total: {total_retrieved}/{limit})"
                    )

            if total_retrieved >= limit:
                break

            # Check if we got fewer videos than requested (end of data)
            if len(videos) < page_limit:
                if self.verbose:
                    logger.info(
                        "Fewer videos returned than requested, end of data reached"
                    )
                break

            if total_retrieved < limit:
                time.sleep(self.rate_limiter.rate_limit)

        # Parallel detail fetching if requested
        if include_details and all_videos:
            video_ids = [video.id for video in all_videos if video.id]
            if video_ids:
                details_map = self._fetch_details_parallel(video_ids)
                self._apply_details_to_videos(all_videos, details_map)

        # Process downloads if requested
        if (download_thumbnails or download_videos) and all_videos:
            all_videos = self._process_downloads(
                all_videos,
                download_thumbnails=download_thumbnails,
                download_videos=download_videos,
                force_redownload=force_redownload,
            )

        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)

            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                download_status = ""
                if download_thumbnails or download_videos:
                    download_parts = []
                    if download_thumbnails:
                        download_parts.append("thumbnails")
                    if download_videos:
                        download_parts.append("videos")
                    download_status = f" and downloaded {'/'.join(download_parts)}"

                logger.info(
                    f"Retrieved {len(df)} member picked videos {detail_status}{download_status}"
                )

            return df

        return self._ensure_consistent_schema(pd.DataFrame())

    def get_trending_hashtags(self, limit: int = 1000) -> pd.DataFrame:
        """Get trending hashtags with automatic pagination.

        Args:
            limit: Maximum number of hashtags to retrieve.

        Returns:
            DataFrame with all hashtags.

        Raises:
            ValidationError: If limit is invalid or exceeds maximum allowed.
            BitChuteAPIError: If the API request fails.

        Example:
            >>> # Get trending hashtags
            >>> hashtags = api.get_trending_hashtags(limit=50)
            >>> print(f"Found {len(hashtags)} trending hashtags")
            >>> print(hashtags[['name', 'rank']].head())
        """
        self.validator.validate_limit(limit, max_limit=1000)

        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")

        all_hashtags = []
        offset = 0
        per_page = 50
        total_retrieved = 0

        while total_retrieved < limit:
            remaining = limit - total_retrieved
            page_limit = min(per_page, remaining)

            payload = {"offset": offset, "limit": page_limit}

            if self.verbose:
                logger.info(
                    f"Fetching trending hashtags: offset={offset}, limit={page_limit}"
                )

            data = self._make_request(
                "beta9/hashtag/trending/", payload, require_token=False
            )
            if not data or "hashtags" not in data or not data["hashtags"]:
                break

            hashtags = []
            for i, tag_data in enumerate(data["hashtags"], 1):
                hashtag = self.data_processor.parse_hashtag(tag_data, offset + i)
                hashtags.append(asdict(hashtag))

            if hashtags:
                all_hashtags.append(pd.DataFrame(hashtags))
                total_retrieved += len(hashtags)
                offset += len(hashtags)

            if len(hashtags) < page_limit:
                break

            if total_retrieved < limit:
                time.sleep(self.rate_limiter.rate_limit)

        if all_hashtags:
            df = pd.concat(all_hashtags, ignore_index=True)
            if self.verbose:
                logger.info(f"Retrieved {len(df)} trending hashtags")
            return df

        return pd.DataFrame()

    def get_videos_by_hashtag(
        self,
        hashtag: str,
        limit: int = 50,
        include_details: bool = False,
        download_thumbnails: bool = False,
        download_videos: bool = False,
        force_redownload: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Get videos associated with a specific hashtag.

        Args:
            hashtag: Hashtag name (with or without # prefix).
            limit: Maximum number of videos to retrieve.
            include_details: Whether to fetch engagement metrics and media URLs.
            download_thumbnails: Whether to download thumbnail images.
            download_videos: Whether to download video files.
            force_redownload: Override instance force_redownload setting.

        Returns:
            DataFrame containing hashtag videos with consistent schema.

        Raises:
            ValidationError: If hashtag format is invalid.
            BitChuteAPIError: If the API request fails.

        Example:
            >>> # Get videos for a hashtag
            >>> videos = api.get_videos_by_hashtag('climate', limit=20)
            >>> print(f"Found {len(videos)} videos for #climate")

            >>> # Get videos with downloads
            >>> videos = api.get_videos_by_hashtag(
            ...     '#bitcoin',
            ...     limit=50,
            ...     include_details=True,
            ...     download_thumbnails=True
            ... )
        """
        # Validate and clean hashtag
        if not hashtag or not isinstance(hashtag, str):
            raise ValidationError("Hashtag must be a non-empty string", "hashtag")

        clean_hashtag = hashtag.lstrip("#").strip()
        if not clean_hashtag:
            raise ValidationError("Hashtag cannot be empty after cleaning", "hashtag")

        if not re.match(r"^[a-zA-Z0-9_-]+$", clean_hashtag):
            raise ValidationError(f"Invalid hashtag format: '{hashtag}'", "hashtag")

        if self.verbose:
            logger.info(f"Fetching videos for hashtag: #{clean_hashtag}")

        all_videos = []
        offset = 0
        per_page = 50

        # Force download details if download videos is True
        if download_videos:
            include_details = True

        while len(all_videos) < limit:
            remaining = limit - len(all_videos)
            page_limit = min(per_page, remaining)

            payload = {"hashtag": clean_hashtag, "offset": offset, "limit": page_limit}

            if self.verbose:
                logger.info(
                    f"Fetching hashtag videos: offset={offset}, limit={page_limit}"
                )

            data = self._make_request(
                "beta/hashtag/videos", payload, require_token=False
            )
            if not data or "videos" not in data or not data["videos"]:
                break

            videos = []
            for i, video_data in enumerate(data["videos"], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(video)

                if len(all_videos) + len(videos) >= limit:
                    break

            if videos:
                all_videos.extend(videos)
                offset += len(videos)

                if len(all_videos) >= limit:
                    all_videos = all_videos[:limit]
                    break

            if len(videos) < page_limit:
                break

            if len(all_videos) < limit:
                time.sleep(self.rate_limiter.rate_limit)

        # Parallel detail fetching if requested
        if include_details and all_videos:
            video_ids = [video.id for video in all_videos if video.id]
            if video_ids:
                details_map = self._fetch_details_parallel(video_ids)
                self._apply_details_to_videos(all_videos, details_map)

        # Process downloads if requested
        if (download_thumbnails or download_videos) and all_videos:
            all_videos = self._process_downloads(
                all_videos,
                download_thumbnails=download_thumbnails,
                download_videos=download_videos,
                force_redownload=force_redownload,
            )

        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)

            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                download_status = ""
                if download_thumbnails or download_videos:
                    download_parts = []
                    if download_thumbnails:
                        download_parts.append("thumbnails")
                    if download_videos:
                        download_parts.append("videos")
                    download_status = f" and downloaded {'/'.join(download_parts)}"

                logger.info(
                    f"Retrieved {len(df)} videos for #{clean_hashtag} {detail_status}{download_status}"
                )

            return df

        return self._ensure_consistent_schema(pd.DataFrame())

    # ================================
    # SEARCH FUNCTIONS
    # ================================

    def search_videos(
        self,
        query: str,
        sensitivity: Union[str, SensitivityLevel] = SensitivityLevel.NORMAL,
        sort: Union[str, SortOrder] = SortOrder.NEW,
        limit: int = 50,
        include_details: bool = False,
        download_thumbnails: bool = False,
        download_videos: bool = False,
        force_redownload: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Search for videos using the BitChute search API.

        Args:
            query: Search query string (max 100 characters).
            sensitivity: Content sensitivity level ('normal', 'nsfw', 'nsfl').
            sort: Sort order ('new', 'old', 'views').
            limit: Maximum number of videos to retrieve.
            include_details: Whether to fetch engagement metrics and media URLs.
            download_thumbnails: Whether to download thumbnail images.
            download_videos: Whether to download video files.
            force_redownload: Override instance force_redownload setting.

        Returns:
            DataFrame containing search results with consistent schema.

        Raises:
            ValidationError: If query is invalid or parameters are out of range.
            BitChuteAPIError: If the API request fails.

        Example:
            >>> # Basic search
            >>> results = api.search_videos('bitcoin', limit=20)
            >>> print(f"Found {len(results)} videos")

            >>> # Advanced search with downloads
            >>> results = api.search_videos(
            ...     'climate change',
            ...     sensitivity='normal',
            ...     sort='views',
            ...     limit=50,
            ...     include_details=True,
            ...     download_thumbnails=True
            ... )
        """
        self.validator.validate_search_query(query)
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")

        if isinstance(sensitivity, SensitivityLevel):
            sensitivity = sensitivity.value
        if isinstance(sort, SortOrder):
            sort = sort.value

        self.validator.validate_sensitivity(sensitivity)
        self.validator.validate_sort_order(sort)

        all_videos = []
        offset = 0
        per_page = 50

        # Force download details if download videos is True
        if download_videos:
            include_details = True

        while len(all_videos) < limit:
            remaining = limit - len(all_videos)
            page_limit = min(per_page, remaining)

            payload = {
                "offset": offset,
                "limit": page_limit,
                "query": query,
                "sensitivity_id": sensitivity,
                "sort": sort,
            }

            if self.verbose:
                logger.info(
                    f"Searching videos '{query}': offset={offset}, limit={page_limit}"
                )

            data = self._make_request("beta/search/videos", payload)
            if not data or "videos" not in data or not data["videos"]:
                break

            videos = []
            for i, video_data in enumerate(data["videos"], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(video)

                if len(all_videos) + len(videos) >= limit:
                    break

            if videos:
                all_videos.extend(videos)
                offset += len(videos)

                if len(all_videos) >= limit:
                    all_videos = all_videos[:limit]
                    break

            if len(videos) < page_limit:
                break

            if len(all_videos) < limit:
                time.sleep(self.rate_limiter.rate_limit)

        # Parallel detail fetching if requested
        if include_details and all_videos:
            video_ids = [video.id for video in all_videos if video.id]
            if video_ids:
                details_map = self._fetch_details_parallel(video_ids)
                self._apply_details_to_videos(all_videos, details_map)

        # Process downloads if requested
        if (download_thumbnails or download_videos) and all_videos:
            all_videos = self._process_downloads(
                all_videos,
                download_thumbnails=download_thumbnails,
                download_videos=download_videos,
                force_redownload=force_redownload,
            )

        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)

            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                download_status = ""
                if download_thumbnails or download_videos:
                    download_parts = []
                    if download_thumbnails:
                        download_parts.append("thumbnails")
                    if download_videos:
                        download_parts.append("videos")
                    download_status = f" and downloaded {'/'.join(download_parts)}"

                logger.info(
                    f"Retrieved {len(df)} videos {detail_status}{download_status}"
                )

            return df

        return self._ensure_consistent_schema(pd.DataFrame())

    def search_channels(
        self,
        query: str,
        sensitivity: Union[str, SensitivityLevel] = SensitivityLevel.NORMAL,
        limit: int = 50,
        include_details: bool = False,
    ) -> pd.DataFrame:
        """Search for channels using the BitChute search API.

        Args:
            query: Search query string.
            sensitivity: Content sensitivity level ('normal', 'nsfw', 'nsfl').
            limit: Maximum number of channels to retrieve.
            include_details: Whether to fetch detailed channel information and social links.

        Returns:
            DataFrame containing channel search results with consistent schema.

        Raises:
            ValidationError: If query is invalid or parameters are out of range.
            BitChuteAPIError: If the API request fails.

        Example:
            >>> # Basic channel search
            >>> channels = api.search_channels('climate', limit=10)
            >>> print(f"Found {len(channels)} channels")

            >>> # Search with detailed info
            >>> detailed = api.search_channels(
            ...     'climate',
            ...     limit=10,
            ...     include_details=True
            ... )
            >>> print(detailed[['name', 'subscriber_count', 'video_count']])
        """
        self.validator.validate_search_query(query)
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")

        if isinstance(sensitivity, SensitivityLevel):
            sensitivity = sensitivity.value

        self.validator.validate_sensitivity(sensitivity)

        all_channels = []
        offset = 0
        per_page = 50

        while len(all_channels) < limit:
            remaining = limit - len(all_channels)
            page_limit = min(per_page, remaining)

            payload = {
                "offset": offset,
                "limit": page_limit,
                "query": query,
                "sensitivity_id": sensitivity,
            }

            if self.verbose:
                logger.info(
                    f"Searching channels '{query}': offset={offset}, limit={page_limit}"
                )

            data = self._make_request("beta/search/channels", payload)
            if not data or "channels" not in data or not data["channels"]:
                break

            channels = []
            for i, channel_data in enumerate(data["channels"], 1):
                channel = self.data_processor.parse_channel(channel_data, offset + i)
                channels.append(channel)

                if len(all_channels) + len(channels) >= limit:
                    break

            if channels:
                all_channels.extend(channels)
                offset += len(channels)

                if len(all_channels) >= limit:
                    all_channels = all_channels[:limit]
                    break

            if len(channels) < page_limit:
                break

            if len(all_channels) < limit:
                time.sleep(self.rate_limiter.rate_limit)

        # Parallel detail fetching if requested
        if include_details and all_channels:
            channel_ids = [channel.id for channel in all_channels if channel.id]
            if channel_ids:
                details_map = self._fetch_channel_details_parallel(channel_ids)
                self._apply_channel_details_to_channels(all_channels, details_map)

        # Convert to DataFrame
        if all_channels:
            channel_dicts = [asdict(channel) for channel in all_channels]
            df = pd.DataFrame(channel_dicts)

            # Ensure consistent schema
            df = self._ensure_consistent_channel_schema(df, include_details)

            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                logger.info(f"Found {len(df)} channels for '{query}' {detail_status}")

            return df

        return self._ensure_consistent_channel_schema(pd.DataFrame(), include_details)

    # ================================
    # CHANNEL FUNCTIONS
    # ================================

    def get_channel_videos(
        self,
        channel_id: str,
        limit: int = 50,
        order_by: str = "latest",
        include_details: bool = False,
        download_thumbnails: bool = False,
        download_videos: bool = False,
        force_redownload: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Get videos from a specific channel.

        Args:
            channel_id: Channel identifier.
            limit: Maximum number of videos to retrieve.
            order_by: Video ordering ('latest', 'popular', 'oldest').
            include_details: Whether to fetch engagement metrics and media URLs.
            download_thumbnails: Whether to download thumbnail images.
            download_videos: Whether to download video files.
            force_redownload: Override instance force_redownload setting.

        Returns:
            DataFrame containing channel videos with consistent schema.

        Raises:
            ValidationError: If channel_id is invalid or parameters are out of range.
            BitChuteAPIError: If the API request fails.

        Example:
            >>> # Get latest videos from a channel
            >>> videos = api.get_channel_videos('channel123', limit=20)
            >>> print(f"Found {len(videos)} videos from channel")

            >>> # Get popular videos with downloads
            >>> videos = api.get_channel_videos(
            ...     'channel123',
            ...     limit=50,
            ...     order_by='popular',
            ...     include_details=True,
            ...     download_thumbnails=True
            ... )
        """
        # Validate inputs
        if not channel_id or not isinstance(channel_id, str):
            raise ValidationError("Channel ID must be a non-empty string", "channel_id")

        if order_by not in ["latest", "popular", "oldest"]:
            raise ValidationError(
                "order_by must be 'latest', 'popular', or 'oldest'", "order_by"
            )

        all_videos = []
        offset = 0
        per_page = 50

        # Force download details if download videos is True
        if download_videos:
            include_details = True

        while len(all_videos) < limit:
            remaining = limit - len(all_videos)
            page_limit = min(per_page, remaining)

            payload = {
                "channel_id": channel_id,
                "offset": offset,
                "limit": page_limit,
                "order_by": order_by,
            }

            if self.verbose:
                logger.info(
                    f"Fetching channel videos: offset={offset}, limit={page_limit}"
                )

            data = self._make_request("beta/channel/videos", payload)
            if not data or "videos" not in data or not data["videos"]:
                break

            videos = []
            for i, video_data in enumerate(data["videos"], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(video)

                if len(all_videos) + len(videos) >= limit:
                    break

            if videos:
                all_videos.extend(videos)
                offset += len(videos)

                if len(all_videos) >= limit:
                    all_videos = all_videos[:limit]
                    break

            if len(videos) < page_limit:
                break

            if len(all_videos) < limit:
                time.sleep(self.rate_limiter.rate_limit)

        # Parallel detail fetching if requested
        if include_details and all_videos:
            video_ids = [video.id for video in all_videos if video.id]
            if video_ids:
                details_map = self._fetch_details_parallel(video_ids)
                self._apply_details_to_videos(all_videos, details_map)

        # Process downloads if requested
        if (download_thumbnails or download_videos) and all_videos:
            all_videos = self._process_downloads(
                all_videos,
                download_thumbnails=download_thumbnails,
                download_videos=download_videos,
                force_redownload=force_redownload,
            )

        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)

            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                download_status = ""
                if download_thumbnails or download_videos:
                    download_parts = []
                    if download_thumbnails:
                        download_parts.append("thumbnails")
                    if download_videos:
                        download_parts.append("videos")
                    download_status = f" and downloaded {'/'.join(download_parts)}"

                logger.info(
                    f"Retrieved {len(df)} videos from channel {channel_id} {detail_status}{download_status}"
                )

            return df

        return self._ensure_consistent_schema(pd.DataFrame())

    # ================================
    # SINGLE ITEM INFO FUNCTIONS
    # ================================

    def get_video_info(
        self,
        video_id: str,
        include_counts: bool = True,
        include_media: bool = True,
        download_thumbnails: bool = False,
        download_videos: bool = False,
        force_redownload: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Get detailed video information as single-row DataFrame for consistency.

        Args:
            video_id: Video ID to fetch details for.
            include_counts: Whether to include like/dislike/view counts.
            include_media: Whether to include media URL.
            download_thumbnails: Whether to download thumbnail image
                (requires enable_downloads=True).
            download_videos: Whether to download video file
                (requires enable_downloads=True).
            force_redownload: Override instance force_redownload setting.

        Returns:
            Single-row DataFrame with video information.

        Raises:
            ValidationError: If video_id format is invalid.
            BitChuteAPIError: If the API request fails.

        Note:
            This method now returns a DataFrame for consistency.
            Use get_video_object() if you need a Video object.

        Example:
            >>> # Get video info as DataFrame
            >>> video_df = api.get_video_info('CLrgZP4RWyly')
            >>> print(video_df[['title', 'view_count', 'duration']])

            >>> # Get video with downloads
            >>> video_df = api.get_video_info(
            ...     'CLrgZP4RWyly',
            ...     include_counts=True,
            ...     download_thumbnails=True,
            ...     download_videos=True
            ... )
        """
        # Get video object first
        video = self.get_video_object(
            video_id=video_id,
            include_counts=include_counts,
            include_media=include_media,
        )

        if not video:
            return self._ensure_consistent_schema(pd.DataFrame())

        # Process downloads if requested
        if download_thumbnails or download_videos:
            videos_list = self._process_downloads(
                [video],
                download_thumbnails=download_thumbnails,
                download_videos=download_videos,
                force_redownload=force_redownload,
            )
            video = videos_list[0] if videos_list else video

        # Convert to single-row DataFrame
        video_dict = asdict(video)
        df = pd.DataFrame([video_dict])
        df = self._ensure_consistent_schema(df)

        if self.verbose:
            download_status = ""
            if download_thumbnails or download_videos:
                download_parts = []
                if download_thumbnails:
                    download_parts.append("thumbnails")
                if download_videos:
                    download_parts.append("videos")
                download_status = f" and downloaded {'/'.join(download_parts)}"

            logger.info(f"Retrieved video info for {video_id}{download_status}")

        return df

    def get_video_object(
        self, video_id: str, include_counts: bool = True, include_media: bool = False
    ) -> Optional[Video]:
        """Get detailed video information as Video object.

        This method provides object-based access for users who need the Video object interface.
        For consistency with other methods, prefer get_video_info() which returns a DataFrame.

        Args:
            video_id: Video ID to fetch details for.
            include_counts: Whether to include like/dislike/view counts.
            include_media: Whether to include media URL.

        Returns:
            Video object or None if not found.

        Raises:
            ValidationError: If video_id format is invalid.
            BitChuteAPIError: If the API request fails.

        Example:
            >>> # Get video as object
            >>> video = api.get_video_object('CLrgZP4RWyly')
            >>> if video:
            ...     print(f"Title: {video.title}")
            ...     print(f"Views: {video.view_count}")
        """
        self.validator.validate_video_id(video_id)

        payload = {"video_id": video_id}

        # Get basic video data from beta9 (doesn't require token)
        data = self._make_request("beta9/video", payload, require_token=False)
        if not data:
            return None

        # Parse video with updated field mappings
        video = self._parse_video_info(data)

        # Get like/dislike counts if requested
        if include_counts:
            try:
                counts_data = self._make_request("beta/video/counts", payload)
                if counts_data:
                    video.like_count = int(counts_data.get("like_count", 0) or 0)
                    video.dislike_count = int(counts_data.get("dislike_count", 0) or 0)
                    # Update view count if more recent
                    new_view_count = int(
                        counts_data.get("view_count", video.view_count)
                        or video.view_count
                    )
                    if new_view_count > video.view_count:
                        video.view_count = new_view_count
            except Exception as e:
                if self.verbose:
                    logger.warning(f"Failed to get counts for {video_id}: {e}")

        # Get media URL if requested
        if include_media:
            try:
                media_data = self._make_request("beta/video/media", payload)
                if media_data:
                    video.media_url = media_data.get("media_url", "")
                    video.media_type = media_data.get("media_type", "")
            except Exception as e:
                if self.verbose:
                    logger.warning(f"Failed to get media URL for {video_id}: {e}")

        return video

    def _parse_video_info(self, data: Dict[str, Any]) -> Video:
        """Parse video details from beta9/video endpoint.

        Args:
            data: Raw video data from API response.

        Returns:
            Parsed Video object with all available fields populated.
        """
        video = Video()

        # Basic fields
        video.id = data.get("video_id", "")
        video.title = data.get("video_name", "")
        video.description = data.get("description", "")
        video.view_count = int(data.get("view_count", 0) or 0)
        video.duration = data.get("duration", "")
        video.upload_date = data.get("date_published", "")
        video.thumbnail_url = data.get("thumbnail_url", "")

        # Category mapping
        video.category_id = data.get("category_id", "")
        video.category = video.category_id

        # Sensitivity
        video.sensitivity = data.get("sensitivity_id", "")

        # State
        video.state = data.get("state_id", "")

        # Channel information
        channel_data = data.get("channel", {})
        if channel_data:
            video.channel_id = channel_data.get("channel_id", "")
            video.channel_name = channel_data.get("channel_name", "")

        # Hashtags with proper parsing
        hashtags_data = data.get("hashtags", [])
        if hashtags_data:
            video.hashtags = []
            for tag_item in hashtags_data:
                if isinstance(tag_item, dict):
                    tag_name = tag_item.get("hashtag_id", "")
                    if tag_name:
                        video.hashtags.append(
                            f"#{tag_name}" if not tag_name.startswith("#") else tag_name
                        )
                elif isinstance(tag_item, str):
                    # Old format: just string
                    video.hashtags.append(
                        f"#{tag_item}" if not tag_item.startswith("#") else tag_item
                    )

        # Flags
        video.is_liked = bool(data.get("is_liked", False))
        video.is_disliked = bool(data.get("is_disliked", False))
        video.is_discussable = bool(data.get("is_discussable", True))

        # Display settings
        video.show_comments = bool(data.get("show_comments", True))
        video.show_adverts = bool(data.get("show_adverts", True))
        video.show_promo = bool(data.get("show_promo", True))
        video.show_rantrave = bool(data.get("show_rantrave", False))

        # Other IDs
        video.profile_id = data.get("profile_id", "")
        video.rumble_id = data.get("rumble_id", "")

        # Build full URL
        if video.id:
            video.video_url = f"https://www.bitchute.com/video/{video.id}/"

        return video

    def get_channel_info(self, channel_id: str) -> pd.DataFrame:
        """Get detailed channel information as single-row DataFrame for consistency.

        Args:
            channel_id: Channel ID to fetch details for.

        Returns:
            Single-row DataFrame with channel information.

        Raises:
            ValidationError: If channel_id format is invalid.
            BitChuteAPIError: If the API request fails.

        Note:
            This method now returns a DataFrame for consistency.
            Use get_channel_object() if you need a Channel object.

        Example:
            >>> # Get channel info as DataFrame
            >>> channel_df = api.get_channel_info('channel123')
            >>> print(channel_df[['name', 'video_count', 'subscriber_count']])
        """
        # Get channel object first
        channel = self.get_channel_object(channel_id)

        if not channel:
            return pd.DataFrame()

        # Convert to single-row DataFrame
        channel_dict = asdict(channel)
        df = pd.DataFrame([channel_dict])

        if self.verbose:
            logger.info(f"Retrieved channel info for {channel_id}")

        return df

    def get_channel_object(self, channel_id: str) -> Optional[Channel]:
        """Get detailed channel information as Channel object.

        This method provides object-based access for users who need the Channel object interface.
        For consistency with other methods, prefer get_channel_info() which returns a DataFrame.

        Args:
            channel_id: Channel ID to fetch details for.

        Returns:
            Channel object or None if not found.

        Raises:
            ValidationError: If channel_id format is invalid.
            BitChuteAPIError: If the API request fails.

        Example:
            >>> # Get channel as object
            >>> channel = api.get_channel_object('channel123')
            >>> if channel:
            ...     print(f"Name: {channel.name}")
            ...     print(f"Videos: {channel.video_count}")
        """
        if not channel_id or not isinstance(channel_id, str):
            raise ValidationError("Channel ID must be a non-empty string", "channel_id")

        payload = {"channel_id": channel_id}

        # Get channel details
        data = self._make_request("beta/channel", payload)
        if not data:
            return None

        # Parse channel with all fields
        channel = self._parse_channel_info(data)

        if self.verbose:
            logger.info(f"Retrieved details for channel: {channel.name}")

        return channel

    def _parse_channel_info(self, data: Dict[str, Any]) -> Channel:
        """Parse channel details from beta/channel endpoint.

        Args:
            data: Raw channel data from API response.

        Returns:
            Parsed Channel object with all available fields populated.
        """
        channel = Channel()

        # Core fields
        channel.id = data.get("channel_id", "")
        channel.name = data.get("channel_name", "")
        channel.description = data.get("description", "")
        channel.url_slug = data.get("url_slug", "")

        # Statistics
        channel.video_count = int(data.get("video_count", 0) or 0)
        channel.view_count = int(data.get("view_count", 0) or 0)
        channel.subscriber_count = str(data.get("subscriber_count", ""))

        # Dates
        channel.created_date = data.get("date_created", "")
        channel.last_video_published = data.get("last_video_published", "")

        # Profile
        channel.profile_id = data.get("profile_id", "")
        channel.profile_name = data.get("profile_name", "")

        # Categories
        channel.category_id = data.get("category_id", "")
        channel.category = channel.category_id
        channel.sensitivity_id = data.get("sensitivity_id", "")
        channel.sensitivity = channel.sensitivity_id

        # State
        channel.state_id = data.get("state_id", "")
        channel.state = channel.state_id

        # URLs
        channel.thumbnail_url = data.get("thumbnail_url", "")
        channel_url = data.get("channel_url", "")
        if channel_url and channel_url.startswith("/"):
            channel.channel_url = f"https://www.bitchute.com{channel_url}"
        else:
            channel.channel_url = channel_url

        # Settings
        channel.membership_level = data.get("membership_level", "Default")
        channel.is_subscribed = bool(data.get("is_subscribed", False))
        channel.is_notified = bool(data.get("is_notified", False))
        channel.show_adverts = bool(data.get("show_adverts", True))
        channel.show_comments = bool(data.get("show_comments", True))
        channel.show_rantrave = bool(data.get("show_rantrave", True))
        channel.live_stream_enabled = bool(data.get("live_stream_enabled", False))
        channel.feature_video = data.get("feature_video")

        return channel

    def get_download_stats(self) -> Dict[str, Any]:
        """Get download statistics if downloads are enabled.

        Returns comprehensive download statistics including success rates,
        total bytes downloaded, deduplication metrics, and operation counts.

        Returns:
            Dict[str, Any]: Dictionary containing download statistics including:
                - downloads_enabled: Whether download functionality is active
                - total_downloads: Total number of download attempts
                - successful_downloads: Number of successful downloads
                - failed_downloads: Number of failed downloads
                - skipped_downloads: Number of skipped (already existing) downloads
                - reused_downloads: Number of reused files (deduplication)
                - total_bytes: Total bytes downloaded
                - success_rate: Success rate as decimal (0.0-1.0)
                - failure_rate: Failure rate as decimal (0.0-1.0)
                - skip_rate: Skip rate as decimal (0.0-1.0)
                - reuse_rate: File reuse rate as decimal (0.0-1.0)
                - unique_content_items: Number of unique content items in database
                - total_bytes_formatted: Human-readable formatted bytes

        Example:
            >>> api = BitChuteAPI(enable_downloads=True, verbose=True)
            >>> 
            >>> # Perform some downloads
            >>> videos = api.get_trending_videos(
            ...     'day', 
            ...     limit=50, 
            ...     download_thumbnails=True
            ... )
            >>> 
            >>> # Check download performance
            >>> stats = api.get_download_stats()
            >>> print(f"Success rate: {stats['success_rate']:.1%}")
            >>> print(f"Total downloaded: {stats['total_bytes_formatted']}")
            >>> print(f"Files reused: {stats['reused_downloads']}")
            >>> print(f"Unique content items: {stats['unique_content_items']}")
        """
        if not self.enable_downloads or not self.download_manager:
            return {
                "downloads_enabled": False,
                "message": "Downloads are not enabled for this API instance"
            }

        stats = self.download_manager.get_stats()
        stats["downloads_enabled"] = True
        return stats


    def get_download_database_info(self) -> Dict[str, Any]:
        """Get information about the download database.

        Returns details about the download database including total entries,
        file count, storage usage, and database file information.

        Returns:
            Dict[str, Any]: Dictionary containing database information including:
                - database_file: Path to database file
                - total_entries: Number of entries in database
                - total_files: Number of tracked files
                - total_size_bytes: Total size of all tracked files in bytes
                - total_size_formatted: Human-readable formatted total size
                - database_exists: Whether database file exists on disk

        Example:
            >>> api = BitChuteAPI(enable_downloads=True)
            >>> 
            >>> # After some downloads
            >>> db_info = api.get_download_database_info()
            >>> print(f"Database contains {db_info['total_entries']} unique items")
            >>> print(f"Total storage: {db_info['total_size_formatted']}")
            >>> print(f"Database file: {db_info['database_file']}")
        """
        if not self.enable_downloads or not self.download_manager:
            return {
                "downloads_enabled": False,
                "message": "Downloads are not enabled for this API instance"
            }

        return self.download_manager.get_database_info()


    def reset_download_stats(self):
        """Reset download statistics to zero.

        Clears all accumulated download statistics including success counts,
        failure counts, and total bytes downloaded. Useful for starting
        fresh statistics collection after a batch operation.

        Note: This only resets statistics, not the download database used
        for deduplication. Use cleanup_download_database() for database operations.

        Example:
            >>> api = BitChuteAPI(enable_downloads=True)
            >>> 
            >>> # Perform some downloads
            >>> videos = api.get_trending_videos('day', limit=20, download_thumbnails=True)
            >>> 
            >>> # Reset stats for new measurement period
            >>> api.reset_download_stats()
            >>> 
            >>> # Perform more downloads with fresh statistics
            >>> more_videos = api.get_popular_videos(limit=30, download_thumbnails=True)
            >>> stats = api.get_download_stats()  # Only includes recent downloads
        """
        if self.enable_downloads and self.download_manager:
            self.download_manager.reset_stats()
            if self.verbose:
                logger.info("Download statistics have been reset")
        elif self.verbose:
            logger.warning("Downloads are not enabled, no statistics to reset")


    def cleanup_download_database(self, verify_files: bool = True):
        """Clean up download database by removing entries for missing files.

        Removes database entries for files that no longer exist on disk,
        helping to keep the database accurate and prevent unnecessary
        storage of orphaned metadata.

        Args:
            verify_files: Whether to verify files still exist on disk.
                If False, no cleanup is performed.

        Example:
            >>> api = BitChuteAPI(enable_downloads=True)
            >>> 
            >>> # After manually deleting some downloaded files
            >>> api.cleanup_download_database(verify_files=True)
            >>> 
            >>> # Check updated database info
            >>> db_info = api.get_download_database_info()
            >>> print(f"Database now contains {db_info['total_entries']} entries")
        """
        if self.enable_downloads and self.download_manager:
            self.download_manager.cleanup_database(verify_files=verify_files)
            if self.verbose:
                logger.info("Download database cleanup completed")
        elif self.verbose:
            logger.warning("Downloads are not enabled, no database to clean up")


    def get_combined_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics combining API usage and download metrics.

        Returns a unified statistics dictionary that includes both API request
        statistics and download performance metrics for complete monitoring.

        Returns:
            Dict[str, Any]: Combined statistics including:
                - api_stats: API request statistics (requests made, errors, etc.)
                - download_stats: Download statistics (if downloads enabled)
                - database_info: Download database information (if downloads enabled)
                - session_info: Session timing and performance metrics

        Example:
            >>> api = BitChuteAPI(enable_downloads=True, verbose=True)
            >>> 
            >>> # Perform various operations
            >>> trending = api.get_trending_videos('day', limit=20, download_thumbnails=True)
            >>> search_results = api.search_videos('bitcoin', limit=50)
            >>> 
            >>> # Get comprehensive stats
            >>> combined = api.get_combined_stats()
            >>> 
            >>> print("=== API Statistics ===")
            >>> api_stats = combined['api_stats']
            >>> print(f"Total requests: {api_stats['requests_made']}")
            >>> print(f"Success rate: {api_stats['success_rate']:.1%}")
            >>> 
            >>> if combined['downloads_enabled']:
            ...     print("\\n=== Download Statistics ===")
            ...     dl_stats = combined['download_stats']
            ...     print(f"Total downloads: {dl_stats['total_downloads']}")
            ...     print(f"Files reused: {dl_stats['reused_downloads']}")
            ...     print(f"Storage saved: {dl_stats['total_bytes_formatted']}")
        """
        # API statistics
        api_stats = self.stats.copy()
        
        # Calculate API success rate
        if api_stats["requests_made"] > 0:
            api_stats["success_rate"] = (
                (api_stats["requests_made"] - api_stats["errors"]) / 
                api_stats["requests_made"]
            )
            api_stats["error_rate"] = api_stats["errors"] / api_stats["requests_made"]
        else:
            api_stats["success_rate"] = 0.0
            api_stats["error_rate"] = 0.0

        # Session information
        current_time = time.time()
        session_duration = current_time - api_stats.get("session_start_time", current_time)
        
        session_info = {
            "session_duration_seconds": session_duration,
            "session_duration_formatted": f"{session_duration / 60:.1f} minutes",
            "requests_per_minute": (
                api_stats["requests_made"] / (session_duration / 60) 
                if session_duration > 0 else 0
            ),
            "last_request_time": api_stats.get("last_request_time", 0),
        }

        combined = {
            "api_stats": api_stats,
            "session_info": session_info,
            "downloads_enabled": self.enable_downloads,
        }

        # Add download statistics if available
        if self.enable_downloads and self.download_manager:
            combined["download_stats"] = self.get_download_stats()
            combined["database_info"] = self.get_download_database_info()
        else:
            combined["download_stats"] = {"downloads_enabled": False}
            combined["database_info"] = {"downloads_enabled": False}

        return combined


    def print_stats_summary(self, show_detailed: bool = False):
        """Print a formatted summary of API and download statistics.

        Displays statistics in a user-friendly format with optional detailed
        breakdown for comprehensive monitoring and debugging.

        Args:
            show_detailed: Whether to show detailed statistics breakdown.
                If False, shows only key metrics summary.

        Example:
            >>> api = BitChuteAPI(enable_downloads=True, verbose=True)
            >>> 
            >>> # Perform operations
            >>> videos = api.get_trending_videos('day', limit=50, download_thumbnails=True)
            >>> 
            >>> # Print summary
            >>> api.print_stats_summary()
            >>> 
            >>> # Print detailed breakdown
            >>> api.print_stats_summary(show_detailed=True)
        """
        stats = self.get_combined_stats()
        
        print("\n" + "="*50)
        print("         BitChute API Statistics Summary")
        print("="*50)
        
        # API Statistics
        api_stats = stats["api_stats"]
        print(f"🌐 API Requests:")
        print(f"   Total requests: {api_stats['requests_made']:,}")
        print(f"   Success rate: {api_stats['success_rate']:.1%}")
        print(f"   Errors: {api_stats['errors']:,}")
        
        # Session Information
        session_info = stats["session_info"]
        print(f"\n⏱️  Session Info:")
        print(f"   Duration: {session_info['session_duration_formatted']}")
        print(f"   Requests/min: {session_info['requests_per_minute']:.1f}")
        
        # Download Statistics
        if stats["downloads_enabled"]:
            dl_stats = stats["download_stats"]
            db_info = stats["database_info"]
            
            print(f"\n📥 Download Performance:")
            print(f"   Total downloads: {dl_stats['total_downloads']:,}")
            print(f"   Success rate: {dl_stats['success_rate']:.1%}")
            print(f"   Files reused: {dl_stats['reused_downloads']:,} ({dl_stats['reuse_rate']:.1%})")
            print(f"   Storage used: {dl_stats['total_bytes_formatted']}")
            print(f"   Unique content: {dl_stats['unique_content_items']:,} items")
            
            if show_detailed:
                print(f"\n📊 Detailed Breakdown:")
                print(f"   Successful downloads: {dl_stats['successful_downloads']:,}")
                print(f"   Failed downloads: {dl_stats['failed_downloads']:,}")
                print(f"   Skipped downloads: {dl_stats['skipped_downloads']:,}")
                print(f"   Database file: {db_info['database_file']}")
                print(f"   Database size: {db_info['total_size_formatted']}")
        else:
            print(f"\n📥 Downloads: Disabled")
        
        print("="*50 + "\n")


    def reset_download_stats(self):
        """Reset download statistics to zero.

        Example:
            >>> # Reset stats after a batch operation
            >>> api.reset_download_stats()
        """
        if self.enable_downloads and self.download_manager:
            self.download_manager.reset_stats()

    
    def debug_token_issues(self) -> Dict[str, Any]:
        """Debug token authentication issues with comprehensive analysis.
        
        Returns:
            Dict containing complete debugging information and recommendations
        """
        if not hasattr(self, 'token_manager'):
            return {"error": "Token manager not available"}
        
        print("🚨 BitChute API Token Debugging")
        print("=" * 50)
        
        # Get comprehensive debug info
        debug_info = self.token_manager.debug_token_status()
        
        # Add API-specific context
        debug_info["api_context"] = {
            "recent_requests": self.stats["requests_made"],
            "recent_errors": self.stats["errors"],
            "last_request_time": self.stats.get("last_request_time", 0),
            "error_rate": self.stats["errors"] / max(1, self.stats["requests_made"])
        }
        
        # Print summary
        print(f"\n📊 Current Status:")
        print(f"   Token available: {debug_info['token_info']['has_token']}")
        print(f"   Token valid: {debug_info['token_info']['is_valid']}")
        print(f"   API requests made: {debug_info['api_context']['recent_requests']}")
        print(f"   API error rate: {debug_info['api_context']['error_rate']:.1%}")
        
        return debug_info


    def fix_token_issues(self) -> bool:
        """Attempt to automatically fix token authentication issues.
        
        Returns:
            bool: True if token issues were resolved, False otherwise
        """
        if not hasattr(self, 'token_manager'):
            print("❌ Token manager not available")
            return False
        
        print("🔧 Attempting to fix token issues...")
        
        # Run comprehensive diagnosis and fix
        fixed_token = self.token_manager.diagnose_and_fix()
        
        if fixed_token:
            print(f"✅ Token issues resolved! New token: {fixed_token[:10]}...")
            
            # Test the fix with a simple API call
            try:
                print("🧪 Testing fix with API call...")
                test_videos = self.get_trending_videos('day', limit=1)
                if len(test_videos) > 0:
                    print("✅ API test successful - fix confirmed!")
                    return True
                else:
                    print("⚠️  API test returned no data - fix may be partial")
                    return False
            except Exception as e:
                print(f"❌ API test failed: {e}")
                return False
        else:
            print("❌ Unable to resolve token issues automatically")
            return False


    def cleanup(self):
        """Clean up resources including sessions and download manager.

        This method should be called when done using the API client to properly
        close connections and clean up temporary resources.

        Example:
            >>> # Proper cleanup
            >>> api = BitChuteAPI()
            >>> try:
            ...     # Use API
            ...     videos = api.get_trending_videos()
            ... finally:
            ...     api.cleanup()
        """
        if hasattr(self, "session"):
            self.session.close()

        if hasattr(self, "download_manager") and self.download_manager:
            self.download_manager.cleanup()

        if hasattr(self, "token_manager"):
            self.token_manager.cleanup()
