"""
BitChute Scraper Core
"""

import time
import logging
import json
import re
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import threading
from enum import Enum

import requests
import pandas as pd
from retrying import retry

from .exceptions import (
    BitChuteAPIError, 
    TokenExtractionError, 
    RateLimitError,
    ValidationError
)
from .models import Video, Channel, Hashtag
from .token_manager import TokenManager
from .utils import DataProcessor, RateLimiter, RequestBuilder
from .validators import InputValidator

# Configure logging
logger = logging.getLogger(__name__)


class SensitivityLevel(Enum):
    """Content sensitivity levels"""
    NORMAL = "normal"
    NSFW = "nsfw" 
    NSFL = "nsfl"


class SortOrder(Enum):
    """Video sort orders"""
    NEW = "new"
    OLD = "old"
    VIEWS = "views"


class VideoSelection(Enum):
    """Video selection types"""
    TRENDING_DAY = "trending-day"
    TRENDING_WEEK = "trending-week"
    TRENDING_MONTH = "trending-month"
    POPULAR = "popular"
    ALL = "all"


class BitChuteAPI:
    """
    BitChute API client
    """
    
    def __init__(
        self, 
        verbose: bool = False,
        cache_tokens: bool = True,
        rate_limit: float = 0.5,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize BitChute API client
        
        Args:
            verbose: Enable verbose logging
            cache_tokens: Cache authentication tokens
            rate_limit: Seconds between requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.verbose = verbose
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize logging
        self._setup_logging()
        
        # Initialize components
        self.token_manager = TokenManager(cache_tokens, verbose)
        self.rate_limiter = RateLimiter(rate_limit)
        self.request_builder = RequestBuilder()
        self.data_processor = DataProcessor()
        self.validator = InputValidator()
        
        # API configuration
        self.base_url = "https://api.bitchute.com/api"
        
        # Setup requests session with optimized settings
        self.session = self._create_session()
        
        # Statistics tracking
        self.stats = {
            'requests_made': 0,
            'cache_hits': 0,
            'errors': 0,
            'last_request_time': 0
        }
    
    def _setup_logging(self):
        """Configure logging based on verbosity"""
        level = logging.INFO if self.verbose else logging.WARNING
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Suppress noisy loggers when not verbose
        if not self.verbose:
            for logger_name in ['selenium', 'urllib3', 'WDM']:
                logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    def _create_session(self) -> requests.Session:
        """Create optimized requests session"""
        session = requests.Session()
        
        # Set headers
        session.headers.update({
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://www.bitchute.com',
            'referer': 'https://www.bitchute.com/',
            'user-agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/138.0.0.0 Safari/537.36'
            )
        })
        
        # Configure retry strategy
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
        self, 
        endpoint: str, 
        payload: Dict[str, Any], 
        require_token: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Make API request with enhanced error handling and retries
        
        Args:
            endpoint: API endpoint
            payload: Request payload
            require_token: Whether authentication token is required
            
        Returns:
            Response data or None if failed
            
        Raises:
            BitChuteAPIError: For API-related errors
            RateLimitError: When rate limited
        """
        # Validate inputs
        self.validator.validate_endpoint(endpoint)
        self.validator.validate_payload(payload)
        
        # Apply rate limiting
        self.rate_limiter.wait()
        
        # Get authentication token if required
        if require_token:
            token = self.token_manager.get_token()
            if token:
                self.session.headers['x-service-info'] = token
            elif self.verbose:
                logger.warning(f"No token available for {endpoint}")
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if self.verbose:
                logger.info(f"API Request: {endpoint}")
            
            response = self.session.post(
                url, 
                json=payload, 
                timeout=self.timeout
            )
            
            # Update statistics
            self.stats['requests_made'] += 1
            self.stats['last_request_time'] = time.time()
            
            # Handle different response codes
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 429:
                self.stats['errors'] += 1
                raise RateLimitError("Rate limit exceeded")
            
            elif response.status_code in [401, 403] and require_token:
                # Token might be invalid, try refresh once
                logger.info("Token invalid, attempting refresh")
                self.token_manager.invalidate_token()
                token = self.token_manager.get_token()
                
                if token:
                    self.session.headers['x-service-info'] = token
                    response = self.session.post(
                        url, 
                        json=payload, 
                        timeout=self.timeout
                    )
                    if response.status_code == 200:
                        return response.json()
            
            # Log error and update stats
            self.stats['errors'] += 1
            error_msg = f"API error: {endpoint} - {response.status_code}"
            
            if self.verbose:
                logger.warning(f"{error_msg}: {response.text[:200]}")
            
            raise BitChuteAPIError(error_msg, response.status_code)
            
        except requests.exceptions.RequestException as e:
            self.stats['errors'] += 1
            error_msg = f"Request failed: {endpoint} - {str(e)}"
            
            if self.verbose:
                logger.error(error_msg)
            
            raise BitChuteAPIError(error_msg) from e


    def get_trending_videos(
        self, 
        timeframe: str = 'day', 
        limit: int = 50,
        per_page: int = 50,
        include_details: bool = False
    ) -> pd.DataFrame:
        """
        Get trending videos with automatic pagination and optional detailed info
        
        Args:
            timeframe: 'day', 'week', or 'month'
            limit: Total number of videos to retrieve (default: 50)
            per_page: Number of videos per API call (default: 50, max: 100)
            include_details: Fetch additional details for each video (counts, media)
            
        Returns:
            DataFrame with all requested videos
        """
        # Validate inputs
        self.validator.validate_timeframe(timeframe)
        self.validator.validate_limit(per_page, max_limit=100)
        
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")
        
        selection_map = {
            'day': VideoSelection.TRENDING_DAY.value,
            'week': VideoSelection.TRENDING_WEEK.value,
            'month': VideoSelection.TRENDING_MONTH.value
        }
        
        all_videos = []
        offset = 0
        total_retrieved = 0
        
        while total_retrieved < limit:
            # Calculate how many to fetch this page
            remaining = limit - total_retrieved
            page_limit = min(per_page, remaining)
            
            payload = {
                "selection": selection_map[timeframe],
                "offset": offset,
                "limit": page_limit,
                "advertisable": True
            }
            
            if self.verbose:
                logger.info(f"Fetching trending videos: offset={offset}, limit={page_limit}")
            
            data = self._make_request("beta/videos", payload)
            if not data or 'videos' not in data or not data['videos']:
                break  # No more videos available
            
            videos = []
            for i, video_data in enumerate(data['videos'], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                
                # Fetch additional details if requested
                if include_details and video.id:
                    self._enrich_video_details(video)
                
                videos.append(asdict(video))
            
            if videos:
                all_videos.append(pd.DataFrame(videos))
                total_retrieved += len(videos)
                offset += len(videos)
                
                if self.verbose:
                    logger.info(f"Retrieved {len(videos)} videos (total: {total_retrieved}/{limit})")
            
            # Check if we got fewer videos than requested (end of data)
            if len(videos) < page_limit:
                break
            
            # Small delay between requests
            if total_retrieved < limit:
                time.sleep(self.rate_limiter.rate_limit)
        
        if all_videos:
            df = pd.concat(all_videos, ignore_index=True)
            if self.verbose:
                logger.info(f"Retrieved {len(df)} trending videos ({timeframe})")
            return df
        
        return pd.DataFrame()

    def get_popular_videos(self, limit: int = 500, per_page: int = 50) -> pd.DataFrame:
        """
        Get popular videos with automatic pagination
        
        Args:
            limit: Total number of videos to retrieve (default: 50)
            per_page: Number of videos per API call (default: 50, max: 100)
            
        Returns:
            DataFrame with all requested videos
        """
        self.validator.validate_limit(per_page, max_limit=100)
        
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")
        
        all_videos = []
        offset = 0
        total_retrieved = 0
        
        while total_retrieved < limit:
            remaining = limit - total_retrieved
            page_limit = min(per_page, remaining)
            
            payload = {
                "selection": VideoSelection.POPULAR.value,
                "offset": offset,
                "limit": page_limit,
                "advertisable": True
            }
            
            if self.verbose:
                logger.info(f"Fetching popular videos: offset={offset}, limit={page_limit}")
            
            data = self._make_request("beta/videos", payload)
            if not data or 'videos' not in data or not data['videos']:
                break
            
            videos = []
            for i, video_data in enumerate(data['videos'], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(asdict(video))
            
            if videos:
                all_videos.append(pd.DataFrame(videos))
                total_retrieved += len(videos)
                offset += len(videos)
            
            if len(videos) < page_limit:
                break
            
            if total_retrieved < limit:
                time.sleep(self.rate_limiter.rate_limit)
        
        if all_videos:
            df = pd.concat(all_videos, ignore_index=True)
            if self.verbose:
                logger.info(f"Retrieved {len(df)} popular videos")
            return df
        
        return pd.DataFrame()

    def get_recent_videos(self, limit: int = 50, per_page: int = 50) -> pd.DataFrame:
        """
        Get recent videos (all videos) with automatic pagination
        
        Args:
            limit: Total number of videos to retrieve (default: 50)
            per_page: Number of videos per API call (default: 50, max: 100)
            
        Returns:
            DataFrame with all requested videos
        """
        self.validator.validate_limit(per_page, max_limit=100)
        
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")
        
        all_videos = []
        offset = 0
        total_retrieved = 0
        
        while total_retrieved < limit:
            remaining = limit - total_retrieved
            page_limit = min(per_page, remaining)
            
            payload = {
                "selection": VideoSelection.ALL.value,
                "offset": offset,
                "limit": page_limit,
                "advertisable": True
            }
            
            if self.verbose:
                logger.info(f"Fetching recent videos: offset={offset}, limit={page_limit}")
            
            data = self._make_request("beta/videos", payload)
            if not data or 'videos' not in data or not data['videos']:
                break
            
            videos = []
            for i, video_data in enumerate(data['videos'], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(asdict(video))
            
            if videos:
                all_videos.append(pd.DataFrame(videos))
                total_retrieved += len(videos)
                offset += len(videos)
                
                if self.verbose:
                    logger.info(f"Retrieved {len(videos)} videos (total: {total_retrieved}/{limit})")
            
            if len(videos) < page_limit:
                break
            
            if total_retrieved < limit:
                time.sleep(self.rate_limiter.rate_limit)
        
        if all_videos:
            df = pd.concat(all_videos, ignore_index=True)
            if self.verbose:
                logger.info(f"Retrieved {len(df)} recent videos")
            return df
        
        return pd.DataFrame()

    def get_all_videos(self, limit: int = 1000, per_page: int = 50) -> pd.DataFrame:
        """
        Get all videos (convenience method for getting many recent videos)
        
        This is a convenience wrapper around get_recent_videos with higher default limit.
        
        Args:
            limit: Total number of videos to retrieve (default: 1000)
            per_page: Number of videos per API call (default: 50, max: 100)
            
        Returns:
            DataFrame with all requested videos
            
        Example:
            >>> # Get 1000 most recent videos
            >>> df = api.get_all_videos()
            
            >>> # Get 5000 videos
            >>> df = api.get_all_videos(limit=5000)
            
            >>> # Get all available videos (up to 10k)
            >>> df = api.get_all_videos(limit=10000)
        """
        if self.verbose:
            logger.info(f"Getting all videos (up to {limit})")
        
        return self.get_recent_videos(limit=limit, per_page=per_page)

    def get_shorts(self, limit: int = 50, per_page: int = 50) -> pd.DataFrame:
        """
        Get short videos with automatic pagination
        
        Args:
            limit: Total number of videos to retrieve (default: 50)
            per_page: Number of videos per API call (default: 50, max: 100)
            
        Returns:
            DataFrame with all requested videos
        """
        self.validator.validate_limit(per_page, max_limit=100)
        
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")
        
        all_videos = []
        offset = 0
        total_retrieved = 0
        
        while total_retrieved < limit:
            remaining = limit - total_retrieved
            page_limit = min(per_page, remaining)
            
            payload = {
                "selection": VideoSelection.ALL.value,
                "offset": offset,
                "limit": page_limit,
                "advertisable": True,
                "is_short": True
            }
            
            if self.verbose:
                logger.info(f"Fetching shorts: offset={offset}, limit={page_limit}")
            
            data = self._make_request("beta/videos", payload)
            if not data or 'videos' not in data or not data['videos']:
                break
            
            videos = []
            for i, video_data in enumerate(data['videos'], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(asdict(video))
            
            if videos:
                all_videos.append(pd.DataFrame(videos))
                total_retrieved += len(videos)
                offset += len(videos)
            
            if len(videos) < page_limit:
                break
            
            if total_retrieved < limit:
                time.sleep(self.rate_limiter.rate_limit)
        
        if all_videos:
            df = pd.concat(all_videos, ignore_index=True)
            if self.verbose:
                logger.info(f"Retrieved {len(df)} shorts")
            return df
        
        return pd.DataFrame()

    def search_videos(
        self, 
        query: str, 
        sensitivity: Union[str, SensitivityLevel] = SensitivityLevel.NORMAL,
        sort: Union[str, SortOrder] = SortOrder.NEW,
        limit: int = 50,
        per_page: int = 50,
        include_details: bool = False
    ) -> pd.DataFrame:
        """
        Search for videos with automatic pagination and optional details
        
        Args:
            query: Search query
            sensitivity: Content sensitivity level
            sort: Sort order
            limit: Total number of results to retrieve (default: 50)
            per_page: Number of results per API call (default: 50, max: 100)
            include_details: Fetch additional details for each video
            
        Returns:
            DataFrame with all search results
        """
        # Validate inputs
        self.validator.validate_search_query(query)
        self.validator.validate_limit(per_page, max_limit=100)
        
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")
        
        # Handle enum conversion
        if isinstance(sensitivity, SensitivityLevel):
            sensitivity = sensitivity.value
        if isinstance(sort, SortOrder):
            sort = sort.value
            
        self.validator.validate_sensitivity(sensitivity)
        self.validator.validate_sort_order(sort)
        
        all_videos = []
        offset = 0
        total_retrieved = 0
        
        while total_retrieved < limit:
            remaining = limit - total_retrieved
            page_limit = min(per_page, remaining)
            
            payload = {
                "offset": offset,
                "limit": page_limit,
                "query": query,
                "sensitivity_id": sensitivity,
                "sort": sort
            }
            
            if self.verbose:
                logger.info(f"Searching videos '{query}': offset={offset}, limit={page_limit}")
            
            data = self._make_request("beta/search/videos", payload)
            if not data or 'videos' not in data or not data['videos']:
                break
            
            videos = []
            for i, video_data in enumerate(data['videos'], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                
                # Fetch additional details if requested
                if include_details and video.id:
                    self._enrich_video_details(video)
                
                videos.append(asdict(video))
            
            if videos:
                all_videos.append(pd.DataFrame(videos))
                total_retrieved += len(videos)
                offset += len(videos)
            
            if len(videos) < page_limit:
                break
            
            if total_retrieved < limit:
                time.sleep(self.rate_limiter.rate_limit)
        
        if all_videos:
            df = pd.concat(all_videos, ignore_index=True)
            if self.verbose:
                logger.info(f"Found {len(df)} videos for '{query}'")
            return df
        
        return pd.DataFrame()

    def search_channels(
        self, 
        query: str, 
        sensitivity: Union[str, SensitivityLevel] = SensitivityLevel.NORMAL,
        limit: int = 50,
        per_page: int = 50
    ) -> pd.DataFrame:
        """
        Search for channels with automatic pagination
        
        Args:
            query: Search query
            sensitivity: Content sensitivity level
            limit: Total number of results to retrieve (default: 50)
            per_page: Number of results per API call (default: 50, max: 100)
            
        Returns:
            DataFrame with all search results
        """
        self.validator.validate_search_query(query)
        self.validator.validate_limit(per_page, max_limit=100)
        
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")
        
        if isinstance(sensitivity, SensitivityLevel):
            sensitivity = sensitivity.value
        
        self.validator.validate_sensitivity(sensitivity)
        
        all_channels = []
        offset = 0
        total_retrieved = 0
        
        while total_retrieved < limit:
            remaining = limit - total_retrieved
            page_limit = min(per_page, remaining)
            
            payload = {
                "offset": offset,
                "limit": page_limit,
                "query": query,
                "sensitivity_id": sensitivity
            }
            
            if self.verbose:
                logger.info(f"Searching channels '{query}': offset={offset}, limit={page_limit}")
            
            data = self._make_request("beta/search/channels", payload)
            if not data or 'channels' not in data or not data['channels']:
                break
            
            channels = []
            for i, channel_data in enumerate(data['channels'], 1):
                channel = self.data_processor.parse_channel(channel_data, offset + i)
                channels.append(asdict(channel))
            
            if channels:
                all_channels.append(pd.DataFrame(channels))
                total_retrieved += len(channels)
                offset += len(channels)
            
            if len(channels) < page_limit:
                break
            
            if total_retrieved < limit:
                time.sleep(self.rate_limiter.rate_limit)
        
        if all_channels:
            df = pd.concat(all_channels, ignore_index=True)
            if self.verbose:
                logger.info(f"Found {len(df)} channels for '{query}'")
            return df
        
        return pd.DataFrame()

    def get_trending_hashtags(self, limit: int = 50, per_page: int = 50) -> pd.DataFrame:
        """
        Get trending hashtags with automatic pagination
        
        Args:
            limit: Total number of hashtags to retrieve (default: 50)
            per_page: Number of hashtags per API call (default: 50, max: 100)
            
        Returns:
            DataFrame with all hashtags
        """
        self.validator.validate_limit(per_page, max_limit=100)
        
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")
        
        all_hashtags = []
        offset = 0
        total_retrieved = 0
        
        while total_retrieved < limit:
            remaining = limit - total_retrieved
            page_limit = min(per_page, remaining)
            
            payload = {
                "offset": offset,
                "limit": page_limit
            }
            
            if self.verbose:
                logger.info(f"Fetching trending hashtags: offset={offset}, limit={page_limit}")
            
            data = self._make_request("beta9/hashtag/trending/", payload, require_token=False)
            if not data or 'hashtags' not in data or not data['hashtags']:
                break
            
            hashtags = []
            for i, tag_data in enumerate(data['hashtags'], 1):
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

    def get_member_picked(self, limit: int = 50) -> pd.DataFrame:
        """
        Get member picked videos
        
        Note: This endpoint doesn't support pagination, so it returns up to the API's limit.
        
        Args:
            limit: Maximum number of videos to retrieve (default: 50)
            
        Returns:
            DataFrame with member picked videos
        """
        self.validator.validate_limit(limit, max_limit=100)
        
        payload = {"limit": limit}
        
        data = self._make_request("beta/member_liked_videos", payload)
        if not data or 'videos' not in data:
            return pd.DataFrame()
        
        videos = []
        for i, video_data in enumerate(data['videos'], 1):
            video = self.data_processor.parse_video(video_data, i)
            videos.append(asdict(video))
        
        df = pd.DataFrame(videos)
        
        if self.verbose:
            logger.info(f"Retrieved {len(videos)} member picked videos")
        
        return df
    
    def get_video_details(
        self, 
        video_id: str, 
        include_counts: bool = True, 
        include_media: bool = False
    ) -> Optional[Video]:
        """
        Get detailed video information with all available fields
        
        Args:
            video_id: Video identifier
            include_counts: Include like/dislike counts
            include_media: Include media download URL
            
        Returns:
            Video object or None if not found
        """
        self.validator.validate_video_id(video_id)
        
        payload = {"video_id": video_id}
        
        # Get basic video data from beta9 (doesn't require token)
        data = self._make_request("beta9/video", payload, require_token=False)
        if not data:
            return None
        
        # Parse video with updated field mappings
        video = self._parse_video_details(data)
        
        # Get like/dislike counts if requested
        if include_counts:
            try:
                counts_data = self._make_request("beta/video/counts", payload)
                if counts_data:
                    video.like_count = int(counts_data.get('like_count', 0) or 0)
                    video.dislike_count = int(counts_data.get('dislike_count', 0) or 0)
                    # Update view count if more recent
                    new_view_count = int(counts_data.get('view_count', video.view_count) or video.view_count)
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
                    video.media_url = media_data.get('media_url', '')
                    video.media_type = media_data.get('media_type', '')
            except Exception as e:
                if self.verbose:
                    logger.warning(f"Failed to get media URL for {video_id}: {e}")
        
        return video


    def _enrich_video_details(self, video: Video):
        """
        Enrich video object with additional details from other endpoints
        
        Args:
            video: Video object to enrich
        """
        try:
            # Get counts
            counts_data = self._make_request("beta/video/counts", {"video_id": video.id})
            if counts_data:
                video.like_count = int(counts_data.get('like_count', 0) or 0)
                video.dislike_count = int(counts_data.get('dislike_count', 0) or 0)
                # Update view count if different
                new_view_count = int(counts_data.get('view_count', video.view_count) or video.view_count)
                if new_view_count > video.view_count:
                    video.view_count = new_view_count
            
            # Small delay to avoid rate limiting
            time.sleep(0.2)
            
            # Get media URL
            media_data = self._make_request("beta/video/media", {"video_id": video.id})
            if media_data:
                video.media_url = media_data.get('media_url', '')
                video.media_type = media_data.get('media_type', '')
                
        except Exception as e:
            if self.verbose:
                logger.warning(f"Failed to enrich video {video.id}: {e}")

    def _parse_video_details(self, data: Dict[str, Any]) -> Video:
        """Parse video details from beta9/video endpoint"""
        video = Video()
        
        # Basic fields
        video.id = data.get('video_id', '')
        video.title = data.get('video_name', '')
        video.description = data.get('description', '')
        video.view_count = int(data.get('view_count', 0) or 0)
        video.duration = data.get('duration', '')
        video.upload_date = data.get('date_published', '')
        video.thumbnail_url = data.get('thumbnail_url', '')
        
        # Category mapping
        video.category_id = data.get('category_id', '')
        video.category = video.category_id  # Use ID as category name for now
        
        # Sensitivity
        video.sensitivity = data.get('sensitivity_id', '')
        
        # State
        video.state = data.get('state_id', '')
        
        # Channel information
        channel_data = data.get('channel', {})
        if channel_data:
            video.channel_id = channel_data.get('channel_id', '')
            video.channel_name = channel_data.get('channel_name', '')
        
        # Hashtags with proper parsing
        hashtags_data = data.get('hashtags', [])
        if hashtags_data:
            video.hashtags = []
            for tag_item in hashtags_data:
                if isinstance(tag_item, dict):
                    # New format: {"hashtag_id": "trump", "hashtag_count": 341}
                    tag_name = tag_item.get('hashtag_id', '')
                    if tag_name:
                        video.hashtags.append(f"#{tag_name}" if not tag_name.startswith('#') else tag_name)
                elif isinstance(tag_item, str):
                    # Old format: just string
                    video.hashtags.append(f"#{tag_item}" if not tag_item.startswith('#') else tag_item)
        
        # Flags
        video.is_liked = bool(data.get('is_liked', False))
        video.is_disliked = bool(data.get('is_disliked', False))
        video.is_discussable = bool(data.get('is_discussable', True))
        
        # Display settings
        video.show_comments = bool(data.get('show_comments', True))
        video.show_adverts = bool(data.get('show_adverts', True))
        video.show_promo = bool(data.get('show_promo', True))
        video.show_rantrave = bool(data.get('show_rantrave', False))
        
        # Other IDs
        video.profile_id = data.get('profile_id', '')
        video.rumble_id = data.get('rumble_id', '')
        
        # Build full URL
        if video.id:
            video.video_url = f"https://www.bitchute.com/video/{video.id}/"
        
        return video


    def get_channel_details(self, channel_id: str) -> Optional[Channel]:
        """
        Get detailed channel information
        
        Args:
            channel_id: Channel identifier
            
        Returns:
            Channel object or None if not found
            
        Example:
            >>> channel = api.get_channel_details('R7juPfa5uBpC')
            >>> print(f"Channel: {channel.name} - {channel.subscriber_count} subscribers")
        """
        # Validate channel ID format
        if not channel_id or not isinstance(channel_id, str):
            raise ValidationError("Channel ID must be a non-empty string", "channel_id")
        
        payload = {"channel_id": channel_id}
        
        # Get channel details
        data = self._make_request("beta/channel", payload)
        if not data:
            return None
        
        # Parse channel with all fields
        channel = self._parse_channel_details(data)
        
        if self.verbose:
            logger.info(f"Retrieved details for channel: {channel.name}")
        
        return channel

    def _parse_channel_details(self, data: Dict[str, Any]) -> Channel:
        """Parse channel details from beta/channel endpoint"""
        channel = Channel()
        
        # Core fields
        channel.id = data.get('channel_id', '')
        channel.name = data.get('channel_name', '')
        channel.description = data.get('description', '')
        channel.url_slug = data.get('url_slug', '')
        
        # Statistics
        channel.video_count = int(data.get('video_count', 0) or 0)
        channel.view_count = int(data.get('view_count', 0) or 0)
        channel.subscriber_count = str(data.get('subscriber_count', ''))
        
        # Dates
        channel.created_date = data.get('date_created', '')
        channel.last_video_published = data.get('last_video_published', '')
        
        # Profile
        channel.profile_id = data.get('profile_id', '')
        channel.profile_name = data.get('profile_name', '')
        
        # Categories
        channel.category_id = data.get('category_id', '')
        channel.category = channel.category_id
        channel.sensitivity_id = data.get('sensitivity_id', '')
        channel.sensitivity = channel.sensitivity_id
        
        # State
        channel.state_id = data.get('state_id', '')
        channel.state = channel.state_id
        
        # URLs
        channel.thumbnail_url = data.get('thumbnail_url', '')
        channel_url = data.get('channel_url', '')
        if channel_url and channel_url.startswith('/'):
            channel.channel_url = f"https://www.bitchute.com{channel_url}"
        else:
            channel.channel_url = channel_url
        
        # Settings
        channel.membership_level = data.get('membership_level', 'Default')
        channel.is_subscribed = bool(data.get('is_subscribed', False))
        channel.is_notified = bool(data.get('is_notified', False))
        channel.show_adverts = bool(data.get('show_adverts', True))
        channel.show_comments = bool(data.get('show_comments', True))
        channel.show_rantrave = bool(data.get('show_rantrave', True))
        channel.live_stream_enabled = bool(data.get('live_stream_enabled', False))
        channel.feature_video = data.get('feature_video')
        
        return channel

    def get_channel_videos(
        self,
        channel_id: str,
        limit: int = 50,
        per_page: int = 50,
        order_by: str = "latest"
    ) -> pd.DataFrame:
        """
        Get videos from a specific channel with pagination
        
        Args:
            channel_id: Channel identifier
            limit: Total number of videos to retrieve (default: 50)
            per_page: Number of videos per API call (default: 50)
            order_by: Sort order ('latest', 'popular', 'oldest')
            
        Returns:
            DataFrame with channel videos
            
        Example:
            >>> videos = api.get_channel_videos('R7juPfa5uBpC', limit=100)
            >>> print(f"Retrieved {len(videos)} videos")
        """
        # Validate inputs
        if not channel_id or not isinstance(channel_id, str):
            raise ValidationError("Channel ID must be a non-empty string", "channel_id")
        
        if order_by not in ['latest', 'popular', 'oldest']:
            raise ValidationError("order_by must be 'latest', 'popular', or 'oldest'", "order_by")
        
        all_videos = []
        offset = 0
        total_retrieved = 0
        
        while total_retrieved < limit:
            remaining = limit - total_retrieved
            page_limit = min(per_page, remaining)
            
            payload = {
                "channel_id": channel_id,
                "offset": offset,
                "limit": page_limit,
                "order_by": order_by
            }
            
            if self.verbose:
                logger.info(f"Fetching channel videos: offset={offset}, limit={page_limit}")
            
            data = self._make_request("beta/channel/videos", payload)
            if not data or 'videos' not in data or not data['videos']:
                break
            
            videos = []
            for i, video_data in enumerate(data['videos'], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(asdict(video))
            
            if videos:
                all_videos.append(pd.DataFrame(videos))
                total_retrieved += len(videos)
                offset += len(videos)
            
            if len(videos) < page_limit:
                break
            
            if total_retrieved < limit:
                time.sleep(self.rate_limiter.rate_limit)
        
        if all_videos:
            df = pd.concat(all_videos, ignore_index=True)
            if self.verbose:
                logger.info(f"Retrieved {len(df)} videos from channel {channel_id}")
            return df
        
        return pd.DataFrame()

    def get_profile_links(self, profile_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Get links associated with a profile
        
        Args:
            profile_id: Profile identifier
            limit: Maximum number of links (default: 10)
            
        Returns:
            List of link dictionaries
            
        Example:
            >>> links = api.get_profile_links('kJFAIAhpktb6')
            >>> for link in links:
            >>>     print(f"{link['title']}: {link['url']}")
        """
        if not profile_id or not isinstance(profile_id, str):
            raise ValidationError("Profile ID must be a non-empty string", "profile_id")
        
        payload = {
            "profile_id": profile_id,
            "offset": 0,
            "limit": limit
        }
        
        data = self._make_request("beta/profile/links", payload)
        if data and 'links' in data:
            return data['links']
        return []



    def get_api_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        uptime = time.time() - self.stats['last_request_time'] if self.stats['last_request_time'] else 0
        
        return {
            'requests_made': self.stats['requests_made'],
            'cache_hits': self.stats['cache_hits'],
            'errors': self.stats['errors'],
            'error_rate': self.stats['errors'] / max(self.stats['requests_made'], 1),
            'uptime_seconds': uptime,
            'token_cached': self.token_manager.has_valid_token()
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources"""
        if self.token_manager:
            self.token_manager.cleanup()
        if hasattr(self, 'session'):
            self.session.close()