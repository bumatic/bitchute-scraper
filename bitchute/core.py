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
        FIXED: Fetch details including hashtags from individual video endpoints
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
                'media_type': '',
                'hashtags': []  # ADD hashtags field
            }
        
        # Temporarily reduce rate limiting for parallel operations
        original_rate_limit = self.rate_limiter.rate_limit
        self.rate_limiter.rate_limit = 0.05
        
        try:
            # BATCH 1: Fetch counts AND hashtags from individual video details
            if self.verbose:
                logger.info("Batch 1: Fetching counts and hashtags...")
            
            def fetch_counts_and_hashtags(video_id: str) -> Dict[str, Any]:
                """Fetch counts AND hashtags for a single video"""
                try:
                    payload = {"video_id": video_id}
                    result = {'video_id': video_id}
                    
                    # Get counts
                    counts_data = self._make_request("beta/video/counts", payload)
                    if counts_data:
                        result.update({
                            'like_count': int(counts_data.get('like_count', 0) or 0),
                            'dislike_count': int(counts_data.get('dislike_count', 0) or 0),
                            'view_count': int(counts_data.get('view_count', 0) or 0)
                        })
                    
                    # Get hashtags from individual video details
                    video_details = self._make_request("beta9/video", payload, require_token=False)
                    if video_details and 'hashtags' in video_details:
                        hashtags = []
                        for tag in video_details['hashtags']:
                            if isinstance(tag, str) and tag.strip():
                                # Format as #hashtag
                                formatted_tag = f"#{tag}" if not tag.startswith('#') else tag
                                hashtags.append(formatted_tag)
                        result['hashtags'] = hashtags
                    
                    return result
                    
                except Exception as e:
                    if self.verbose:
                        logger.warning(f"Failed to fetch details for {video_id}: {e}")
                
                return {'video_id': video_id}
            
            # Execute counts and hashtags in parallel
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(video_ids))) as executor:
                future_to_id = {
                    executor.submit(fetch_counts_and_hashtags, video_id): video_id
                    for video_id in video_ids
                }
                
                for future in as_completed(future_to_id):
                    result = future.result()
                    if result and 'video_id' in result:
                        video_id = result['video_id']
                        # Update all fields in details_map
                        for key in ['like_count', 'dislike_count', 'view_count', 'hashtags']:
                            if key in result:
                                details_map[video_id][key] = result[key]
            
            # BATCH 2: Fetch media URLs (unchanged)
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
            
            # Execute media in parallel
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(video_ids))) as executor:
                future_to_id = {
                    executor.submit(fetch_media, video_id): video_id
                    for video_id in video_ids
                }
                
                for future in as_completed(future_to_id):
                    result = future.result()
                    if result and 'video_id' in result:
                        video_id = result['video_id']
                        for key in ['media_url', 'media_type']:
                            if key in result:
                                details_map[video_id][key] = result[key]
        
        finally:
            # Restore original rate limiting
            self.rate_limiter.rate_limit = original_rate_limit
        
        # Log results
        if self.verbose:
            duration = time.time() - start_time
            success_counts = sum(1 for d in details_map.values() if d['like_count'] > 0 or d['view_count'] > 0)
            success_media = sum(1 for d in details_map.values() if d['media_url'])
            success_hashtags = sum(1 for d in details_map.values() if d['hashtags'])
            logger.info(f"Parallel fetch completed in {duration:.2f}s: {success_counts}/{len(video_ids)} counts, {success_media}/{len(video_ids)} media URLs, {success_hashtags}/{len(video_ids)} hashtags")
        
        return details_map

    def _apply_details_to_videos(self, videos: List, details_map: Dict[str, Dict[str, Any]]):
        """
        FIXED: Apply fetched details including hashtags to Video objects
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
                
                # FIXED: Apply hashtags
                if details['hashtags']:
                    video.hashtags = details['hashtags']

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

    def _fetch_channel_details_parallel(self, channel_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch detailed channel information and profile links in parallel
        
        Args:
            channel_ids: List of channel IDs to enrich
            
        Returns:
            Dict mapping channel_id to detailed info including social links
        """
        if not channel_ids:
            return {}
        
        if self.verbose:
            logger.info(f"Fetching detailed info for {len(channel_ids)} channels with {self.max_workers} workers...")
        
        start_time = time.time()
        details_map = {}
        
        # Initialize all channel IDs in results
        for channel_id in channel_ids:
            details_map[channel_id] = {
                'channel_id': channel_id,
                'full_details': {},
                'social_links': []
            }
        
        # Temporarily reduce rate limiting for parallel operations
        original_rate_limit = self.rate_limiter.rate_limit
        self.rate_limiter.rate_limit = 0.05
        
        try:
            # BATCH 1: Fetch full channel details
            if self.verbose:
                logger.info("Batch 1: Fetching full channel details...")
            
            def fetch_channel_details(channel_id: str) -> Dict[str, Any]:
                """Fetch full channel details for a single channel"""
                try:
                    payload = {"channel_id": channel_id}
                    data = self._make_request("beta/channel", payload)
                    if data:
                        return {
                            'channel_id': channel_id,
                            'full_details': data
                        }
                except Exception as e:
                    if self.verbose:
                        logger.warning(f"Failed to fetch channel details for {channel_id}: {e}")
                
                return {'channel_id': channel_id}
            
            # Execute channel details in parallel
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(channel_ids))) as executor:
                future_to_id = {
                    executor.submit(fetch_channel_details, channel_id): channel_id
                    for channel_id in channel_ids
                }
                
                for future in as_completed(future_to_id):
                    result = future.result()
                    if result and 'channel_id' in result:
                        channel_id = result['channel_id']
                        if 'full_details' in result:
                            details_map[channel_id]['full_details'] = result['full_details']
            
            # BATCH 2: Fetch profile links for channels that have profile_id
            if self.verbose:
                logger.info("Batch 2: Fetching profile links...")
            
            def fetch_profile_links(channel_info: Dict[str, Any]) -> Dict[str, Any]:
                """Fetch profile links for a channel"""
                channel_id = channel_info['channel_id']
                full_details = channel_info['full_details']
                
                try:
                    profile_id = full_details.get('profile_id')
                    if profile_id:
                        payload = {
                            "profile_id": profile_id,
                            "offset": 0,
                            "limit": 20  # Get up to 20 social links
                        }
                        data = self._make_request("beta/profile/links", payload)
                        if data and 'links' in data:
                            return {
                                'channel_id': channel_id,
                                'social_links': data['links']
                            }
                except Exception as e:
                    if self.verbose:
                        logger.warning(f"Failed to fetch profile links for {channel_id}: {e}")
                
                return {'channel_id': channel_id, 'social_links': []}
            
            # Prepare channels that have profile_id for link fetching
            channels_with_profiles = []
            for channel_id, details in details_map.items():
                if details['full_details'].get('profile_id'):
                    channels_with_profiles.append({
                        'channel_id': channel_id,
                        'full_details': details['full_details']
                    })
            
            # Execute profile links in parallel
            if channels_with_profiles:
                with ThreadPoolExecutor(max_workers=min(self.max_workers, len(channels_with_profiles))) as executor:
                    future_to_id = {
                        executor.submit(fetch_profile_links, channel_info): channel_info['channel_id']
                        for channel_info in channels_with_profiles
                    }
                    
                    for future in as_completed(future_to_id):
                        result = future.result()
                        if result and 'channel_id' in result:
                            channel_id = result['channel_id']
                            details_map[channel_id]['social_links'] = result['social_links']
        
        finally:
            # Restore original rate limiting
            self.rate_limiter.rate_limit = original_rate_limit
        
        # Log results
        if self.verbose:
            duration = time.time() - start_time
            success_details = sum(1 for d in details_map.values() if d['full_details'])
            success_links = sum(1 for d in details_map.values() if d['social_links'])
            logger.info(f"Channel details fetch completed in {duration:.2f}s: {success_details}/{len(channel_ids)} details, {success_links}/{len(channel_ids)} social links")
        
        return details_map

    def _apply_channel_details_to_channels(self, channels: List, details_map: Dict[str, Dict[str, Any]]):
        """
        Apply fetched detailed info to Channel objects
        
        Args:
            channels: List of Channel objects to enrich
            details_map: Details from _fetch_channel_details_parallel()
        """
        for channel in channels:
            if channel.id in details_map:
                details = details_map[channel.id]
                
                # Apply full channel details (overwrite with more complete data)
                full_details = details.get('full_details', {})
                if full_details:
                    # Update all fields with complete data
                    channel.description = full_details.get('description', channel.description)
                    channel.video_count = int(full_details.get('video_count', channel.video_count) or 0)
                    channel.view_count = int(full_details.get('view_count', channel.view_count) or 0)
                    channel.subscriber_count = str(full_details.get('subscriber_count', channel.subscriber_count))
                    channel.created_date = full_details.get('date_created', channel.created_date)
                    channel.last_video_published = full_details.get('last_video_published', channel.last_video_published)
                    channel.profile_id = full_details.get('profile_id', channel.profile_id)
                    channel.profile_name = full_details.get('profile_name', channel.profile_name)
                    channel.membership_level = full_details.get('membership_level', channel.membership_level)
                    channel.url_slug = full_details.get('url_slug', channel.url_slug)
                    channel.is_subscribed = bool(full_details.get('is_subscribed', channel.is_subscribed))
                    channel.is_notified = bool(full_details.get('is_notified', channel.is_notified))
                    channel.live_stream_enabled = bool(full_details.get('live_stream_enabled', channel.live_stream_enabled))
                    channel.feature_video = full_details.get('feature_video', channel.feature_video)
                
                # Apply social links (new field)
                social_links = details.get('social_links', [])
                channel.social_links = social_links  # This will now work because we added the field

    def _ensure_consistent_channel_schema(self, df: pd.DataFrame, include_details: bool = False):
        """
        FIXED: Ensure DataFrame has consistent channel schema
        
        Args:
            df: DataFrame to standardize
            include_details: Whether detailed fields should be included
            
        Returns:
            DataFrame with consistent columns and types
        """
        # Basic channel columns (always present)
        basic_columns = {
            'id': '',
            'name': '', 
            'description': '',
            'url_slug': '',
            'video_count': 0,
            'subscriber_count': '',
            'view_count': 0,
            'created_date': '',
            'last_video_published': '',
            'profile_id': '',
            'profile_name': '',
            'category': '',
            'category_id': '',
            'sensitivity': '',
            'sensitivity_id': '',
            'thumbnail_url': '',
            'channel_url': '',
            'state': '',
            'state_id': '',
            'scrape_timestamp': 0.0
        }
        
        # Additional columns when include_details=True
        if include_details:
            detailed_columns = {
                'membership_level': 'Default',
                'is_verified': False,
                'is_subscribed': False,
                'is_notified': False,
                'show_adverts': True,
                'show_comments': True,
                'show_rantrave': True,
                'live_stream_enabled': False,
                'feature_video': None,
                'social_links': []  # NEW: List of social media links
            }
            basic_columns.update(detailed_columns)
        
        # Handle empty DataFrame
        if df.empty:
            # Create empty DataFrame with correct columns
            empty_df = pd.DataFrame(columns=list(basic_columns.keys()))
            return empty_df
        
        # Add missing columns with default values - FIXED approach
        for col, default_val in basic_columns.items():
            if col not in df.columns:
                # FIXED: Use scalar for non-list defaults, appropriate value for lists
                if isinstance(default_val, list):
                    # For list columns like social_links, create list for each row
                    df[col] = [default_val.copy() for _ in range(len(df))]
                else:
                    # For scalar values, use the default
                    df[col] = default_val
        
        # Ensure correct column order
        df = df.reindex(columns=list(basic_columns.keys()), fill_value='')
        
        # Convert types
        numeric_cols = ['video_count', 'view_count', 'scrape_timestamp']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        if include_details:
            boolean_cols = ['is_verified', 'is_subscribed', 'is_notified', 
                           'show_adverts', 'show_comments', 'show_rantrave', 'live_stream_enabled']
            for col in boolean_cols:
                if col in df.columns:
                    df[col] = df[col].astype(bool)
        
        return df

    # ================================
    # Get Platform Recommendations
    # ================================

    def get_trending_videos(
        self, 
        timeframe: str = 'day', 
        limit: int = 50,
        include_details: bool = False
    ) -> pd.DataFrame:
        """
        Get trending videos with optional parallel detail fetching
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
            # FIXED: Calculate how many to fetch this page
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
                break
            
            videos = []
            for i, video_data in enumerate(data['videos'], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(video)
                
                # FIXED: Stop when we reach the exact limit
                if len(all_videos) + len(videos) >= limit:
                    videos = videos[:limit - len(all_videos)]
                    break
            
            if videos:
                all_videos.extend(videos)
                total_retrieved = len(all_videos)  # FIXED: Use actual count
                offset += len(videos)
                
                if self.verbose:
                    logger.info(f"Retrieved {len(videos)} videos (total: {total_retrieved}/{limit})")
            
            # FIXED: Check if we reached the exact limit
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
        """FIXED: Get popular videos with EXACT limit respect"""
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")
        
        all_videos = []
        offset = 0
        per_page = 50
        
        while len(all_videos) < limit:
            # Calculate exact amount needed
            remaining = limit - len(all_videos)
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
                
                # FIXED: Stop exactly at limit
                if len(all_videos) + len(videos) >= limit:
                    break
            
            if videos:
                all_videos.extend(videos)
                offset += len(videos)
                
                # FIXED: Stop exactly at limit
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
        """FIXED: Get recent videos with EXACT limit respect"""
        if limit < 1:
            raise ValidationError("Total limit must be at least 1", "limit")
        
        all_videos = []
        offset = 0
        per_page = 50
        
        while len(all_videos) < limit:
            remaining = limit - len(all_videos)
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
                videos.append(video)
                
                # FIXED: Stop exactly at limit
                if len(all_videos) + len(videos) >= limit:
                    break
            
            if videos:
                all_videos.extend(videos)
                offset += len(videos)
                
                # FIXED: Stop exactly at limit
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

    def get_videos_by_hashtag(self, hashtag: str, limit: int = 50, include_details: bool = False) -> pd.DataFrame:
        """FIXED: Get hashtag videos with EXACT limit respect"""
        # Validate and clean hashtag
        if not hashtag or not isinstance(hashtag, str):
            raise ValidationError("Hashtag must be a non-empty string", "hashtag")
        
        clean_hashtag = hashtag.lstrip('#').strip()
        if not clean_hashtag:
            raise ValidationError("Hashtag cannot be empty after cleaning", "hashtag")
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', clean_hashtag):
            raise ValidationError(f"Invalid hashtag format: '{hashtag}'", "hashtag")
        
        if self.verbose:
            logger.info(f"Fetching videos for hashtag: #{clean_hashtag}")
        
        all_videos = []
        offset = 0
        per_page = 50
        
        while len(all_videos) < limit:
            remaining = limit - len(all_videos)
            page_limit = min(per_page, remaining)
            
            payload = {
                "hashtag": clean_hashtag,
                "offset": offset,
                "limit": page_limit
            }
            
            if self.verbose:
                logger.info(f"Fetching hashtag videos: offset={offset}, limit={page_limit}")
            
            data = self._make_request("beta/hashtag/videos", payload, require_token=False)
            if not data or 'videos' not in data or not data['videos']:
                break
            
            videos = []
            for i, video_data in enumerate(data['videos'], 1):
                video = self.data_processor.parse_video(video_data, offset + i)
                videos.append(video)
                
                # FIXED: Stop exactly at limit
                if len(all_videos) + len(videos) >= limit:
                    break
            
            if videos:
                all_videos.extend(videos)
                offset += len(videos)
                
                # FIXED: Stop exactly at limit
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
        
        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)
            
            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                logger.info(f"Retrieved {len(df)} videos for #{clean_hashtag} {detail_status}")
            
            return df
        
        return self._ensure_consistent_schema(pd.DataFrame())


    # ================================
    # SEARCH FUNCTIONS
    # ================================
    
    def search_videos(self, query: str, sensitivity: Union[str, SensitivityLevel] = SensitivityLevel.NORMAL,
                 sort: Union[str, SortOrder] = SortOrder.NEW, limit: int = 50, include_details: bool = False) -> pd.DataFrame:
        """FIXED: Search videos with EXACT limit respect"""
        # Validate inputs
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
        
        while len(all_videos) < limit:
            remaining = limit - len(all_videos)
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
                videos.append(video)
                
                # FIXED: Stop exactly at limit
                if len(all_videos) + len(videos) >= limit:
                    break
            
            if videos:
                all_videos.extend(videos)
                offset += len(videos)
                
                # FIXED: Stop exactly at limit
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
        
        # Convert to DataFrame with consistent schema
        if all_videos:
            video_dicts = [asdict(video) for video in all_videos]
            df = pd.DataFrame(video_dicts)
            df = self._ensure_consistent_schema(df)
            
            if self.verbose:
                detail_status = "with details" if include_details else "without details"
                logger.info(f"Found {len(df)} videos for '{query}' {detail_status}")
            
            return df
        
        return self._ensure_consistent_schema(pd.DataFrame())

    def search_channels(
        self, 
        query: str, 
        sensitivity: Union[str, SensitivityLevel] = SensitivityLevel.NORMAL,
        limit: int = 50,
        include_details: bool = False  # NEW PARAMETER
    ) -> pd.DataFrame:
        """
        Search for channels with optional parallel detail fetching
        
        Args:
            query: Search query
            sensitivity: Content sensitivity level
            limit: Total number of results to retrieve (default: 50)
            include_details: Fetch full channel details and profile links (default: False)
            
        Returns:
            DataFrame with all search results and detailed info if requested
            
        Example:
            >>> # Basic search
            >>> channels = api.search_channels('climate', limit=10)
            
            >>> # With detailed info (subscriber counts, descriptions, social links)
            >>> detailed = api.search_channels('climate', limit=10, include_details=True)
            >>> print(detailed.columns)  # Includes full channel details + social_links
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
                channels.append(channel)
                
                # Stop exactly at limit
                if len(all_channels) + len(channels) >= limit:
                    break
            
            if channels:
                all_channels.extend(channels)
                offset += len(channels)
                
                # Stop exactly at limit
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

    def get_channel_videos(self, channel_id: str, limit: int = 50, order_by: str = "latest", include_details: bool = False) -> pd.DataFrame:
        """FIXED: Get channel videos with EXACT limit respect"""
        # Validate inputs
        if not channel_id or not isinstance(channel_id, str):
            raise ValidationError("Channel ID must be a non-empty string", "channel_id")
        
        if order_by not in ['latest', 'popular', 'oldest']:
            raise ValidationError("order_by must be 'latest', 'popular', or 'oldest'", "order_by")
        
        all_videos = []
        offset = 0
        per_page = 50
        
        while len(all_videos) < limit:
            remaining = limit - len(all_videos)
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
                
                # FIXED: Stop exactly at limit
                if len(all_videos) + len(videos) >= limit:
                    break
            
            if videos:
                all_videos.extend(videos)
                offset += len(videos)
                
                # FIXED: Stop exactly at limit
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

    def get_video_info(self, video_id: str, include_counts: bool = True, include_media: bool = False) -> Optional[Video]:
        """Get detailed video information with all available fields"""
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

    def _parse_video_info(self, data: Dict[str, Any]) -> Video:
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
        video.category = video.category_id
        
        # Sensitivity
        video.sensitivity = data.get('sensitivity_id', '')
        
        # State
        video.state = data.get('state_id', '')
        
        # Channel information
        channel_data = data.get('channel', {})
        if channel_data:
            video.channel_id = channel_data.get('channel_id', '')
            video.channel_name = channel_data.get('channel_name', '')
        
        # FIXED: Hashtags with proper parsing
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

    def get_channel_info(self, channel_id: str) -> Optional[Channel]:
        """Get detailed channel information"""
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

