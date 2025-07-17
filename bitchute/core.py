"""
BitChute Scraper Core - Decluttered and Standardized
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
    BitChute API client with standardized interface and unified parallel processing
    """
    
    def __init__(
        self, 
        verbose: bool = False,
        cache_tokens: bool = True,
        rate_limit: float = 0.5,
        timeout: int = 30,
        max_retries: int = 3,
        max_workers: int = 8
    ):
        """
        Initialize BitChute API client
        
        Args:
            verbose: Enable verbose logging
            cache_tokens: Cache authentication tokens
            rate_limit: Seconds between requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            max_workers: Maximum concurrent workers for parallel operations
        """
        self.verbose = verbose
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_workers = max_workers
        
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
        """Make API request with enhanced error handling and retries"""
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
            
        except RateLimitError:
            raise
        except requests.exceptions.RequestException as e:
            self.stats['requests_made'] += 1
            self.stats['errors'] += 1
            self.stats['last_request_time'] = time.time()
            
            error_msg = f"Request failed: {endpoint} - {str(e)}"
            
            if self.verbose:
                logger.error(error_msg)
            
            raise BitChuteAPIError(error_msg) from e
        
        except Exception as e:
            if isinstance(e, (BitChuteAPIError, RateLimitError, ValidationError)):
                raise
                
            self.stats['requests_made'] += 1
            self.stats['errors'] += 1
            self.stats['last_request_time'] = time.time()
            
            error_msg = f"Unexpected error: {endpoint} - {str(e)}"
            
            if self.verbose:
                logger.error(error_msg)
            
            raise BitChuteAPIError(error_msg) from e

    def _fetch_details_parallel(self, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Unified parallel details fetching for all video functions
        
        Strategy: 2-batch approach for optimal performance
        1. Fetch all counts first (like_count, dislike_count, view_count)
        2. Fetch all media URLs second (media_url, media_type)
        
        Args:
            video_ids: List of video IDs to enrich
            
        Returns:
            Dict mapping video_id to details dict with all fields
        """
        if not video_ids:
            return {}
        
        if self.verbose:
            logger.info(f"Fetching details for {len(video_ids)} videos with {self.max_workers} workers...")
        
        start_time = time.time()
        details_map = {}
        
        # Initialize all video IDs in results
        for video_id in video_ids:
            details_map[video_id] = {
                'video_id': video_id,
                'like_count': 0,
                'dislike_count': 0,
                'view_count': 0,
                'media_url': '',
                'media_type': ''
            }
        
        # BATCH 1: Fetch counts for all videos
        if self.verbose:
            logger.info("Batch 1: Fetching counts...")
        
        def fetch_counts(video_id: str) -> Dict[str, Any]:
            """Fetch counts for a single video"""
            try:
                payload = {"video_id": video_id}
                data = self._make_request("beta/video/counts", payload)
                if data:
                    return {
                        'video_id': video_id,
                        'like_count': int(data.get('like_count', 0) or 0),
                        'dislike_count': int(data.get('dislike_count', 0) or 0),
                        'view_count': int(data.get('view_count', 0) or 0)
                    }
            except Exception as e:
                if self.verbose:
                    logger.warning(f"Failed to fetch counts for {video_id}: {e}")
            
            return {'video_id': video_id}
        
        # Execute counts batch
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_id = {
                executor.submit(fetch_counts, video_id): video_id
                for video_id in video_ids
            }
            
            for future in as_completed(future_to_id):
                result = future.result()
                if result and 'video_id' in result:
                    video_id = result['video_id']
                    # Update counts in details_map
                    for key in ['like_count', 'dislike_count', 'view_count']:
                        if key in result:
                            details_map[video_id][key] = result[key]
        
        # BATCH 2: Fetch media URLs for all videos
        if self.verbose:
            logger.info("Batch 2: Fetching media URLs...")
        
        def fetch_media(video_id: str) -> Dict[str, Any]:
            """Fetch media URL for a single video"""
            try:
                payload = {"video_id": video_id}
                data = self._make_request("beta/video/media", payload)
                if data:
                    return {
                        'video_id': video_id,
                        'media_url': data.get('media_url', ''),
                        'media_type': data.get('media_type', '')
                    }
            except Exception as e:
                if self.verbose:
                    logger.warning(f"Failed to fetch media for {video_id}: {e}")
            
            return {'video_id': video_id}
        
        # Execute media batch
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_id = {
                executor.submit(fetch_media, video_id): video_id
                for video_id in video_ids
            }
            
            for future in as_completed(future_to_id):
                result = future.result()
                if result and 'video_id' in result:
                    video_id = result['video_id']
                    # Update media info in details_map
                    for key in ['media_url', 'media_type']:
                        if key in result:
                            details_map[video_id][key] = result[key]
        
        # Log results
        if self.verbose:
            duration = time.time() - start_time
            success_counts = sum(1 for d in details_map.values() if d['like_count'] > 0 or d['view_count'] > 0)
            success_media = sum(1 for d in details_map.values() if d['media_url'])
            logger.info(f"Parallel fetch completed in {duration:.2f}s: {success_counts}/{len(video_ids)} counts, {success_media}/{len(video_ids)} media URLs")
        
        return details_map

    def _apply_details_to_videos(self, videos: List, details_map: Dict[str, Dict[str, Any]]):
        """
        Apply fetched details to Video objects
        
        Args:
            videos: List of Video objects to enrich
            details_map: Details from _fetch_details_parallel()
        """
        for video in videos:
            if video.id in details_map:
                details = details_map[video.id]
                
                # Apply counts (update if higher than current)
                if details['like_count'] > 0:
                    video.like_count = details['like_count']
                if details['dislike_count'] > 0:
                    video.dislike_count = details['dislike_count']
                if details['view_count'] > video.view_count:
                    video.view_count = details['view_count']
                
                # Apply media info
                if details['media_url']:
                    video.media_url = details['media_url']
                if details['media_type']:
                    video.media_type = details['media_type']

    def _ensure_consistent_schema(self, df):
        """
        Ensure DataFrame has consistent schema across all video functions
        
        Args:
            df: DataFrame to standardize
            
        Returns:
            DataFrame with consistent columns and types
        """
        # Define expected columns with default values
        expected_columns = {
            'id': '',
            'title': '',
            'description': '',
            'view_count': 0,
            'duration': '',
            'thumbnail_url': '',
            'video_url': '',
            'channel_id': '',
            'channel_name': '',
            'category': '',
            'upload_date': '',
            'hashtags': [],
            'is_short': False,
            'like_count': 0,
            'dislike_count': 0,
            'media_url': '',
            'media_type': ''
        }
        
        # Add missing columns with default values
        for col, default_val in expected_columns.items():
            if col not in df.columns:
                df[col] = default_val
        
        # Ensure correct column order
        df = df.reindex(columns=list(expected_columns.keys()), fill_value='')
        
        # Convert types
        numeric_cols = ['view_count', 'like_count', 'dislike_count']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        boolean_cols = ['is_short']
        for col in boolean_cols:
            df[col] = df[col].astype(bool)
        
        return df

    # ================================
    # STANDARDIZED VIDEO FUNCTIONS
    # ================================

    def get_trending_videos(
        self, 
        timeframe: str = 'day', 
        limit: int = 50,
        include_details: bool = False
    ) -> pd.DataFrame:
        """
        Get trending videos with optional parallel detail fetching
        
        Args:
            timeframe: 'day', 'week', or 'month'
            limit: Total number of videos to retrieve (default: 50)
            include_details: Fetch like/dislike counts and media URLs (default: False)
            
        Returns:
            DataFrame with all requested videos and consistent schema
        """
        # Validate inputs
        self.validator.validate_timeframe(timeframe)
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")
        
        selection_map = {
            'day': VideoSelection.TRENDING_DAY.value,
            'week': VideoSelection.TRENDING_WEEK.value,
            'month': VideoSelection.TRENDING_MONTH.value
        }
        
        all_videos = []
        offset = 0
        per_page = 50
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
                videos.append(video)
            
            if videos:
                all_videos.extend(videos)
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
        
        # Parallel detail fetching if requested
        if include_details and all_videos:
            video_ids = [video.id for video in all_videos if video.id]
            if video_ids:
                details_map = self._fetch_details_parallel(video_ids)
                self._apply_details_to_videos(all_videos, details_map)
        
        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)
            
            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                logger.info(f"Retrieved {len(df)} trending videos ({timeframe}) {detail_status}")
            
            return df
        
        return self._ensure_consistent_schema(pd.DataFrame())

    def get_popular_videos(self, limit: int = 50, include_details: bool = False) -> pd.DataFrame:
        """
        Get popular videos with optional parallel detail fetching
        
        Args:
            limit: Total number of videos to retrieve (default: 50)
            include_details: Fetch like/dislike counts and media URLs (default: False)
            
        Returns:
            DataFrame with all requested videos and consistent schema
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
        
        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)
            
            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                logger.info(f"Retrieved {len(df)} popular videos {detail_status}")
            
            return df
        
        return self._ensure_consistent_schema(pd.DataFrame())

    def get_recent_videos(self, limit: int = 50, include_details: bool = False) -> pd.DataFrame:
        """
        Get recent videos with optional parallel detail fetching
        
        Args:
            limit: Total number of videos to retrieve (default: 50)
            include_details: Fetch like/dislike counts and media URLs (default: False)
            
        Returns:
            DataFrame with all requested videos and consistent schema
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
                "advertisable": True
            }
            
            if self.verbose:
                logger.info(f"Fetching recent videos: offset={offset}, limit={page_limit}")
            
            data = self._make_request("beta/videos", payload)
            if not data or 'videos' not in data or not data['videos']:
                if self.verbose:
                    logger.info(f"No more videos available at offset {offset}")
                break  # No more videos available
            
            videos = []
            for i, video_data in enumerate(data['videos'], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(video)
            
            if videos:
                all_videos.extend(videos)
                total_retrieved += len(videos)
                offset += len(videos)
                
                if self.verbose:
                    logger.info(f"Retrieved {len(videos)} videos (total: {total_retrieved}/{limit})")
            
            # Check if we got fewer videos than requested (end of data)
            if len(videos) < page_limit:
                if self.verbose:
                    logger.info(f"Got {len(videos)} videos, expected {page_limit}. End of data reached.")
                break
            
            if total_retrieved < limit:
                time.sleep(self.rate_limiter.rate_limit)
        
        # Parallel detail fetching if requested
        if include_details and all_videos:
            video_ids = [video.id for video in all_videos if video.id]
            if video_ids:
                details_map = self._fetch_details_parallel(video_ids)
                self._apply_details_to_videos(all_videos, details_map)
        
        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)
            
            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                logger.info(f"Retrieved {len(df)} recent videos {detail_status}")
            
            return df
        
        return self._ensure_consistent_schema(pd.DataFrame())

    def get_all_videos(self, limit: int = 1000, include_details: bool = False) -> pd.DataFrame:
        """
        Get all videos (convenience method for getting many recent videos)
        
        This is a convenience wrapper around get_recent_videos with higher default limit.
        
        Args:
            limit: Total number of videos to retrieve (default: 1000)
            include_details: Fetch like/dislike counts and media URLs (default: False)
            
        Returns:
            DataFrame with all requested videos and consistent schema
            
        Example:
            >>> # Get 1000 most recent videos
            >>> df = api.get_all_videos()
            
            >>> # Get 5000 videos with details
            >>> df = api.get_all_videos(limit=5000, include_details=True)
        """
        if self.verbose:
            logger.info(f"Getting all videos (up to {limit})")
        
        return self.get_recent_videos(limit=limit, include_details=include_details)

    def get_short_videos(self, limit: int = 50, include_details: bool = False) -> pd.DataFrame:
        """
        Get short videos with optional parallel detail fetching
        
        Args:
            limit: Total number of videos to retrieve (default: 50)
            include_details: Fetch like/dislike counts and media URLs (default: False)
            
        Returns:
            DataFrame with all requested videos and consistent schema
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
                "is_short": True
            }
            
            if self.verbose:
                logger.info(f"Fetching short videos: offset={offset}, limit={page_limit}")
            
            data = self._make_request("beta/videos", payload)
            if not data or 'videos' not in data or not data['videos']:
                break
            
            videos = []
            for i, video_data in enumerate(data['videos'], 1):
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
        
        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)
            
            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                logger.info(f"Retrieved {len(df)} short videos {detail_status}")
            
            return df
        
        return self._ensure_consistent_schema(pd.DataFrame())

    def get_member_picked_videos(self, limit: int = 50, include_details: bool = False) -> pd.DataFrame:
        """
        Get member picked videos with optional parallel detail fetching
        
        Note: This endpoint doesn't support pagination, so it returns up to the API's limit.
        
        Args:
            limit: Maximum number of videos to retrieve (default: 50)
            include_details: Fetch like/dislike counts and media URLs (default: False)
            
        Returns:
            DataFrame with member picked videos and consistent schema
        """
        self.validator.validate_limit(limit, max_limit=100)
        
        payload = {"limit": limit}
        
        data = self._make_request("beta/member_liked_videos", payload)
        if not data or 'videos' not in data:
            return self._ensure_consistent_schema(pd.DataFrame())
        
        videos = []
        for i, video_data in enumerate(data['videos'], 1):
            video = self.data_processor.parse_video(video_data, i)
            videos.append(video)
        
        # Parallel detail fetching if requested
        if include_details and videos:
            video_ids = [video.id for video in videos if video.id]
            if video_ids:
                details_map = self._fetch_details_parallel(video_ids)
                self._apply_details_to_videos(videos, details_map)
        
        # Convert to DataFrame with consistent schema
        if videos:
            video_dicts = [asdict(video) for video in videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)
            
            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                logger.info(f"Retrieved {len(df)} member picked videos {detail_status}")
            
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
        include_details: bool = False
    ) -> pd.DataFrame:

        self.validator.validate_search_query(query)
        
        # Step 1: Fetch videos for hashtag with pagination
        all_videos = []
        offset = 0
        per_page = 50
        total_retrieved = 0
        
        while total_retrieved < limit:
            remaining = limit - total_retrieved
            page_limit = min(per_page, remaining)
            
            payload = {
                "query": query,
                "offset": offset,
                "limit": page_limit
            }
            
            if self.verbose:
                logger.info(f"Fetching hashtag videos: offset={offset}, limit={page_limit}")
            
            # Use hashtag-specific endpoint
            data = self._make_request("beta/search/videos", payload, require_token=False)
            if not data or 'videos' not in data or not data['videos']:
                if self.verbose:
                    logger.info(f"No more videos found for query {query} at offset {offset}")
                break
            
            videos = []
            for i, video_data in enumerate(data['videos'], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(video)
            
            if videos:
                all_videos.extend(videos)
                total_retrieved += len(videos)
                offset += len(videos)
                
                if self.verbose:
                    logger.info(f"Retrieved {len(videos)} videos (total: {total_retrieved}/{limit})")
            
            # Check if we got fewer videos than requested (end of data)
            if len(videos) < page_limit:
                break
            
            if total_retrieved < limit:
                time.sleep(self.rate_limiter.rate_limit)
        
        # Step 2: Parallel detail fetching if requested
        if include_details and all_videos:
            video_ids = [video.id for video in all_videos if video.id]
            if video_ids:
                details_map = self._fetch_details_parallel(video_ids)
                self._apply_details_to_videos(all_videos, details_map)
        
        # Step 3: Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)
            
            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                logger.info(f"Retrieved {len(df)} videos for #{clean_hashtag} {detail_status}")
            
            return df
        
        # Return empty DataFrame with consistent schema
        return self._ensure_consistent_schema(pd.DataFrame())

    def get_trending_hashtags(self, limit: int = 50) -> pd.DataFrame:
        """
        Get trending hashtags with automatic pagination
        
        Args:
            limit: Total number of hashtags to retrieve (default: 50)
            
        Returns:
            DataFrame with all hashtags
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

    # ================================
    # CHANNEL FUNCTIONS
    # ================================

    def get_channel_videos(
        self,
        channel_id: str,
        limit: int = 50,
        order_by: str = "latest",
        include_details: bool = False
    ) -> pd.DataFrame:
        """
        Get videos from a specific channel with optional parallel detail fetching
        
        Args:
            channel_id: Channel identifier
            limit: Total number of videos to retrieve (default: 50)
            order_by: Sort order ('latest', 'popular', 'oldest')
            include_details: Fetch like/dislike counts and media URLs (default: False)
            
        Returns:
            DataFrame with channel videos and consistent schema
            
        Example:
            >>> videos = api.get_channel_videos('R7juPfa5uBpC', limit=100, include_details=True)
            >>> print(f"Retrieved {len(videos)} videos")
        """
        # Validate inputs
        if not channel_id or not isinstance(channel_id, str):
            raise ValidationError("Channel ID must be a non-empty string", "channel_id")
        
        if order_by not in ['latest', 'popular', 'oldest']:
            raise ValidationError("order_by must be 'latest', 'popular', or 'oldest'", "order_by")
        
        all_videos = []
        offset = 0
        per_page = 50
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
        
        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)
            
            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                logger.info(f"Retrieved {len(df)} videos from channel {channel_id} {detail_status}")
            
            return df
        
        return self._ensure_consistent_schema(pd.DataFrame())

    # ================================
    # SINGLE ITEM INFO FUNCTIONS
    # ================================

    def get_video_info(self, video_id: str) -> pd.DataFrame:
        """
        Get detailed information for a single video as single-row DataFrame
        
        Args:
            video_id: Video identifier
            
        Returns:
            Single-row DataFrame with complete video information
            Returns empty DataFrame if video not found
            
        Example:
            >>> # Get detailed info for a specific video
            >>> df = api.get_video_info('CLrgZP4RWyly')
            >>> if not df.empty:
            >>>     print(f"Video: {df.iloc[0]['title']}")
            >>>     print(f"Views: {df.iloc[0]['view_count']:,}")
        """
        # Validate video ID
        self.validator.validate_video_id(video_id)
        
        if self.verbose:
            logger.info(f"Fetching detailed info for video: {video_id}")
        
        try:
            # Get detailed video information (includes counts, media, all fields)
            video = self.get_video_details(video_id, include_counts=True, include_media=True)
            
            if video:
                # Convert single Video object to single-row DataFrame
                video_dict = asdict(video)
                df = pd.DataFrame([video_dict])
                df = self._ensure_consistent_schema(df)
                
                if self.verbose:
                    logger.info(f"Retrieved info for video: {video.title[:50]}...")
                
                return df
            else:
                if self.verbose:
                    logger.warning(f"Video not found: {video_id}")
                
        except Exception as e:
            if self.verbose:
                logger.error(f"Failed to get video info for {video_id}: {e}")
        
        # Return empty DataFrame with consistent schema
        return self._ensure_consistent_schema(pd.DataFrame())

    def get_channel_info(self, channel_id: str) -> pd.DataFrame:
        """
        Get detailed information for a single channel as single-row DataFrame
        
        Args:
            channel_id: Channel identifier
            
        Returns:
            Single-row DataFrame with complete channel information
            Returns empty DataFrame if channel not found
            
        Example:
            >>> # Get detailed info for a specific channel
            >>> df = api.get_channel_info('R7juPfa5uBpC')
            >>> if not df.empty:
            >>>     print(f"Channel: {df.iloc[0]['name']}")
            >>>     print(f"Videos: {df.iloc[0]['video_count']}")
        """
        # Validate channel ID
        if not channel_id or not isinstance(channel_id, str):
            raise ValidationError("Channel ID must be a non-empty string", "channel_id")
        
        channel_id = channel_id.strip()
        if not channel_id:
            raise ValidationError("Channel ID cannot be empty", "channel_id")
        
        if self.verbose:
            logger.info(f"Fetching detailed info for channel: {channel_id}")
        
        try:
            # Get detailed channel information
            channel = self.get_channel_details(channel_id)
            
            if channel:
                # Convert single Channel object to single-row DataFrame
                channel_dict = asdict(channel)
                df = pd.DataFrame([channel_dict])
                
                # Ensure consistent column schema for channels
                expected_columns = {
                    'id': '', 'name': '', 'description': '', 'url_slug': '',
                    'video_count': 0, 'subscriber_count': '', 'view_count': 0,
                    'created_date': '', 'last_video_published': '', 'profile_id': '',
                    'profile_name': '', 'category': '', 'category_id': '', 'sensitivity': '',
                    'sensitivity_id': '', 'thumbnail_url': '', 'channel_url': '', 'state': '',
                    'state_id': '', 'membership_level': 'Default', 'is_verified': False,
                    'is_subscribed': False, 'is_notified': False, 'show_adverts': True,
                    'show_comments': True, 'show_rantrave': True, 'live_stream_enabled': False,
                    'feature_video': None, 'scrape_timestamp': 0.0
                }
                
                # Add missing columns with default values
                for col, default_val in expected_columns.items():
                    if col not in df.columns:
                        df[col] = default_val
                
                # Ensure correct column order
                df = df.reindex(columns=list(expected_columns.keys()), fill_value='')
                
                # Convert types
                numeric_cols = ['video_count', 'view_count', 'scrape_timestamp']
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                boolean_cols = ['is_verified', 'is_subscribed', 'is_notified', 
                               'show_adverts', 'show_comments', 'show_rantrave', 'live_stream_enabled']
                for col in boolean_cols:
                    df[col] = df[col].astype(bool)
                
                if self.verbose:
                    logger.info(f"Retrieved info for channel: {channel.name}")
                
                return df
            else:
                if self.verbose:
                    logger.warning(f"Channel not found: {channel_id}")
                
        except Exception as e:
            if self.verbose:
                logger.error(f"Failed to get channel info for {channel_id}: {e}")
        
        # Return empty DataFrame with consistent schema
        return pd.DataFrame()

