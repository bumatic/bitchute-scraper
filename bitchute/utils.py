"""
BitChute Scraper Utilities Module - Cleaned and Simplified
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
    """Thread-safe rate limiter for API requests"""
    
    def __init__(self, rate_limit: float = 0.5):
        """
        Initialize rate limiter
        
        Args:
            rate_limit: Minimum seconds between requests
        """
        self.rate_limit = rate_limit
        self.last_request = 0
        self._lock = threading.Lock()
    
    def wait(self):
        """Wait if necessary to respect rate limit"""
        with self._lock:
            elapsed = time.time() - self.last_request
            if elapsed < self.rate_limit:
                sleep_time = self.rate_limit - elapsed
                time.sleep(sleep_time)
            self.last_request = time.time()


class RequestBuilder:
    """Builds and validates API request payloads"""
    
    @staticmethod
    def build_video_request(
        selection: str,
        offset: int = 0,
        limit: int = 20,
        advertisable: bool = True,
        is_short: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Build video request payload"""
        payload = {
            "selection": selection,
            "offset": offset,
            "limit": limit,
            "advertisable": advertisable
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
        sort: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build search request payload"""
        payload = {
            "offset": offset,
            "limit": limit,
            "query": query,
            "sensitivity_id": sensitivity
        }
        
        if sort:
            payload["sort"] = sort
            
        return payload
    
    @staticmethod
    def build_hashtag_request(
        offset: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Build hashtag request payload"""
        return {
            "offset": offset,
            "limit": limit
        }
    
    @staticmethod
    def build_video_detail_request(video_id: str) -> Dict[str, Any]:
        """Build video detail request payload"""
        return {"video_id": video_id}


class DataProcessor:
    """Processes and parses API response data with correct field mappings"""
    
    def parse_video(self, data: Dict[str, Any], rank: int = 0) -> Video:
        """
        Parse video data from API response with correct field mapping
        
        Args:
            data: Raw video data from API
            rank: Video ranking/position
            
        Returns:
            Parsed Video object
        """
        video = Video()
        
        try:
            # Core identifiers
            video.id = self._safe_get(data, 'video_id', '')
            video.title = self._safe_get(data, 'video_name', '')
            video.description = self._safe_get(data, 'description', '')
            
            # View count
            video.view_count = self._safe_int(data.get('view_count', 0))
            
            # Duration
            video.duration = self._safe_get(data, 'duration', '')
            
            # Upload date
            video.upload_date = self._safe_get(data, 'date_published', '')
            
            # Thumbnail
            video.thumbnail_url = self._safe_get(data, 'thumbnail_url', '')
            
            # Category - use category_id if available
            video.category_id = self._safe_get(data, 'category_id', '')
            video.category = video.category_id or self._safe_get(data, 'category', '')
            
            # Sensitivity
            video.sensitivity = self._safe_get(data, 'sensitivity_id', '')
            
            # State
            video.state = self._safe_get(data, 'state_id', '')
            
            # Check for is_short/is_shorts
            video.is_short = bool(data.get('is_short', data.get('is_shorts', False)))
            
            # Channel information from nested channel object
            channel = data.get('channel', {})
            if isinstance(channel, dict):
                video.channel_id = self._safe_get(channel, 'channel_id', '')
                video.channel_name = self._safe_get(channel, 'channel_name', '')
            else:
                # Fallback to old structure if exists
                uploader = data.get('uploader', {})
                if isinstance(uploader, dict):
                    video.channel_id = self._safe_get(uploader, 'id', '')
                    video.channel_name = self._safe_get(uploader, 'name', '')
            
            # Profile ID
            video.profile_id = self._safe_get(data, 'profile_id', '')
            
            # FIXED: Hashtags processing - handle new format properly
            hashtags_data = data.get('hashtags', data.get('tags', []))
            if hashtags_data:
                video.hashtags = []
                for tag_item in hashtags_data:
                    if isinstance(tag_item, dict):
                        # New format: {"hashtag_id": "trump", "hashtag_count": 341}
                        tag_name = tag_item.get('hashtag_id', '')
                        if tag_name:
                            formatted_tag = f"#{tag_name}" if not tag_name.startswith('#') else tag_name
                            video.hashtags.append(formatted_tag)
                    elif isinstance(tag_item, str) and tag_item:
                        # Old format: just string
                        formatted_tag = f"#{tag_item}" if not tag_item.startswith('#') else tag_item
                        video.hashtags.append(formatted_tag)
            
            # Engagement metrics (may be populated later)
            video.like_count = self._safe_int(data.get('like_count', 0))
            video.dislike_count = self._safe_int(data.get('dislike_count', 0))
            
            # Flags from video details
            video.is_liked = bool(data.get('is_liked', False))
            video.is_disliked = bool(data.get('is_disliked', False))
            video.is_discussable = bool(data.get('is_discussable', True))
            
            # Display settings
            video.show_comments = bool(data.get('show_comments', True))
            video.show_adverts = bool(data.get('show_adverts', True))
            video.show_promo = bool(data.get('show_promo', True))
            video.show_rantrave = bool(data.get('show_rantrave', False))
            
            # External IDs
            video.rumble_id = self._safe_get(data, 'rumble_id', '')
            
            # URLs
            if video.id:
                video.video_url = f"https://www.bitchute.com/video/{video.id}/"
            elif data.get('video_url'):
                # If relative URL provided, make it absolute
                relative_url = data.get('video_url', '')
                if relative_url.startswith('/'):
                    video.video_url = f"https://www.bitchute.com{relative_url}"
                else:
                    video.video_url = relative_url
            
            # Media URL and type if present
            video.media_url = self._safe_get(data, 'media_url', '')
            video.media_type = self._safe_get(data, 'media_type', '')
            
        except Exception as e:
            logger.warning(f"Error parsing video data: {e}")
        
        return video
    
    def parse_channel(self, data: Dict[str, Any], rank: int = 0) -> Channel:
        """
        UPDATED: Parse channel data with social_links support
        """
        channel = Channel()
        
        try:
            # ... all existing parsing logic remains the same ...
            
            # Core identifiers
            channel.id = self._safe_get(data, 'channel_id', self._safe_get(data, 'id', ''))
            channel.name = self._safe_get(data, 'channel_name', self._safe_get(data, 'name', data.get('title', '')))
            channel.description = self._safe_get(data, 'description', '')
            channel.url_slug = self._safe_get(data, 'url_slug', '')
            
            # Statistics
            channel.video_count = self._safe_int(data.get('video_count', 0))
            channel.subscriber_count = str(data.get('subscriber_count', ''))
            channel.view_count = self._safe_int(data.get('view_count', 0))
            
            # Dates
            channel.created_date = self._safe_get(data, 'date_created', data.get('created_at', ''))
            channel.last_video_published = self._safe_get(data, 'last_video_published', '')
            
            # Profile information
            channel.profile_id = self._safe_get(data, 'profile_id', '')
            channel.profile_name = self._safe_get(data, 'profile_name', '')
            
            # If profile is nested object
            profile = data.get('profile', {})
            if isinstance(profile, dict):
                channel.profile_id = channel.profile_id or self._safe_get(profile, 'profile_id', '')
                channel.profile_name = channel.profile_name or self._safe_get(profile, 'profile_name', '')
            
            # Categories
            channel.category_id = self._safe_get(data, 'category_id', '')
            channel.category = channel.category_id or self._safe_get(data, 'category', '')
            channel.sensitivity_id = self._safe_get(data, 'sensitivity_id', '')
            channel.sensitivity = channel.sensitivity_id or self._safe_get(data, 'sensitivity', '')
            
            # State
            channel.state_id = self._safe_get(data, 'state_id', '')
            channel.state = channel.state_id or self._safe_get(data, 'state', '')
            
            # URLs
            channel.thumbnail_url = self._safe_get(data, 'thumbnail_url', '')
            
            # Build channel URL
            if channel.id:
                channel.channel_url = f"https://www.bitchute.com/channel/{channel.id}/"
            elif data.get('channel_url'):
                # If relative URL provided, make it absolute
                relative_url = data.get('channel_url', '')
                if relative_url.startswith('/'):
                    channel.channel_url = f"https://www.bitchute.com{relative_url}"
                else:
                    channel.channel_url = relative_url
            
            # Additional settings
            channel.membership_level = self._safe_get(data, 'membership_level', 'Default')
            channel.is_verified = bool(data.get('is_verified', False))
            channel.is_subscribed = bool(data.get('is_subscribed', False))
            channel.is_notified = bool(data.get('is_notified', False))
            
            # Display settings
            channel.show_adverts = bool(data.get('show_adverts', True))
            channel.show_comments = bool(data.get('show_comments', True))
            channel.show_rantrave = bool(data.get('show_rantrave', True))
            
            # Features
            channel.live_stream_enabled = bool(data.get('live_stream_enabled', False))
            channel.feature_video = data.get('feature_video')
            
            # NEW: Initialize social_links (will be populated later by _apply_channel_details_to_channels)
            channel.social_links = []
            
        except Exception as e:
            logger.warning(f"Error parsing channel data: {e}")
        
        return channel

    def parse_hashtag(self, data: Dict[str, Any], rank: int = 0) -> Hashtag:
        """
        Parse hashtag data from API response
        
        Args:
            data: Raw hashtag data from API
            rank: Hashtag ranking/position
            
        Returns:
            Parsed Hashtag object
        """
        hashtag = Hashtag()
        
        try:
            # Handle both old and new formats
            if 'hashtag_id' in data:
                # New format from video details
                hashtag.name = self._safe_get(data, 'hashtag_id', '')
                hashtag.video_count = self._safe_int(data.get('hashtag_count', 0))
            else:
                # Old format
                hashtag.name = self._safe_get(data, 'name', '')
                hashtag.video_count = self._safe_int(data.get('video_count', 0))
            
            hashtag.rank = rank
            
            # Build hashtag URL
            if hashtag.name:
                clean_name = hashtag.name.lstrip('#')
                hashtag.url = f"https://www.bitchute.com/hashtag/{clean_name}/"
            
        except Exception as e:
            logger.warning(f"Error parsing hashtag data: {e}")
        
        return hashtag
    
    @staticmethod
    def _safe_get(data: Dict[str, Any], key: str, default: str = '') -> str:
        """Safely get string value from dict"""
        value = data.get(key, default)
        return str(value) if value is not None else default
    
    @staticmethod
    def _safe_int(value: Any) -> int:
        """Safely convert value to integer"""
        try:
            if value is None:
                return 0
            return int(float(str(value)))
        except (ValueError, TypeError):
            return 0


class PaginationHelper:
    """Helper for handling paginated API responses"""
    
    @staticmethod
    def get_multiple_pages(
        api_method,
        max_pages: int = 5,
        per_page: int = 50,
        **kwargs
    ) -> pd.DataFrame:
        """Get multiple pages of data from an API method"""
        all_data = []
        
        for page in range(max_pages):
            offset = page * per_page
            
            try:
                # Call API method with offset
                if 'limit' in api_method.__code__.co_varnames:
                    df = api_method(limit=per_page, offset=offset, **kwargs)
                else:
                    df = api_method(limit=per_page, **kwargs)
                
                if df.empty:
                    logger.info(f"Page {page + 1}: No data returned, stopping pagination")
                    break
                
                all_data.append(df)
                
                logger.info(f"Page {page + 1}: {len(df)} items")
                
                # Check if we got fewer items than requested (end of data)
                if len(df) < per_page:
                    logger.info(f"Got {len(df)} items, expected {per_page}. End of data reached.")
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
    """Process multiple items concurrently"""
    
    @staticmethod
    def process_video_details(
        api_client,
        video_ids: List[str], 
        max_workers: int = 5,
        include_counts: bool = True,
        include_media: bool = False
    ) -> List[Video]:
        """
        Get details for multiple videos concurrently (External API - users can import this)
        
        Note: Internal functions use the unified _fetch_details_parallel() method
        
        Args:
            api_client: BitChute API client instance
            video_ids: List of video IDs to process
            max_workers: Maximum concurrent workers
            include_counts: Include like/dislike counts
            include_media: Include media URLs
            
        Returns:
            List of Video objects
        """
        videos = []
        
        def get_video_details_thread(video_id):
            try:
                return api_client.get_video_details(
                    video_id, 
                    include_counts=include_counts,
                    include_media=include_media
                )
            except Exception as e:
                logger.warning(f"Failed to get details for {video_id}: {e}")
                return None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {
                executor.submit(get_video_details_thread, vid): vid 
                for vid in video_ids
            }
            
            for future in concurrent.futures.as_completed(future_to_id):
                video = future.result()
                if video:
                    videos.append(video)
        
        logger.info(f"Retrieved details for {len(videos)}/{len(video_ids)} videos")
        return videos


class DataExporter:
    """Export data to various formats"""
    
    @staticmethod
    def export_data(
        df: pd.DataFrame, 
        filename: str, 
        formats: List[str] = None
    ) -> Dict[str, str]:
        """
        Export DataFrame to various formats
        
        Args:
            df: DataFrame to export
            filename: Base filename (without extension)
            formats: List of formats to export ('csv', 'json', 'xlsx', 'parquet')
            
        Returns:
            Dict mapping format to filepath
        """
        if formats is None:
            formats = ['csv']
        
        exported = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for fmt in formats:
            try:
                filepath = f"{filename}_{timestamp}.{fmt}"
                
                if fmt == 'csv':
                    df.to_csv(filepath, index=False, encoding='utf-8')
                    
                elif fmt == 'json':
                    df.to_json(filepath, orient='records', indent=2, force_ascii=False)
                    
                elif fmt == 'xlsx':
                    df.to_excel(filepath, index=False, engine='openpyxl')
                    
                elif fmt == 'parquet':
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
    """Filter and process content based on various criteria"""
    
    @staticmethod
    def filter_by_views(df: pd.DataFrame, min_views: int = 0, max_views: int = None) -> pd.DataFrame:
        """Filter videos by view count"""
        if df.empty or 'view_count' not in df.columns:
            return df
        
        filtered = df[df['view_count'] >= min_views]
        
        if max_views is not None:
            filtered = filtered[filtered['view_count'] <= max_views]
        
        return filtered
    
    @staticmethod
    def filter_by_duration(df: pd.DataFrame, min_seconds: int = 0, max_seconds: int = None) -> pd.DataFrame:
        """Filter videos by duration"""
        if df.empty or 'duration' not in df.columns:
            return df
        
        def duration_to_seconds(duration_str):
            try:
                return ContentFilter._parse_duration(duration_str)
            except:
                return 0
        
        df_copy = df.copy()
        df_copy['duration_seconds'] = df_copy['duration'].apply(duration_to_seconds)
        
        filtered = df_copy[df_copy['duration_seconds'] >= min_seconds]
        
        if max_seconds is not None:
            filtered = filtered[filtered['duration_seconds'] <= max_seconds]
        
        # Remove the temporary column
        return filtered.drop('duration_seconds', axis=1)
    
    @staticmethod
    def filter_by_keywords(df: pd.DataFrame, keywords: List[str], column: str = 'title') -> pd.DataFrame:
        """Filter content by keywords in specified column"""
        if df.empty or column not in df.columns:
            return df
        
        if not keywords:
            return df
        
        # Create case-insensitive regex pattern
        pattern = '|'.join(re.escape(keyword) for keyword in keywords)
        
        filtered = df[df[column].str.contains(pattern, case=False, na=False)]
        return filtered
    
    @staticmethod
    def filter_by_channel(df: pd.DataFrame, channels: List[str]) -> pd.DataFrame:
        """Filter videos by channel names"""
        if df.empty or 'channel_name' not in df.columns:
            return df
        
        if not channels:
            return df
        
        filtered = df[df['channel_name'].isin(channels)]
        return filtered
    
    @staticmethod
    def filter_by_date_range(
        df: pd.DataFrame, 
        start_date: str = None, 
        end_date: str = None,
        date_column: str = 'upload_date'
    ) -> pd.DataFrame:
        """Filter by date range"""
        if df.empty or date_column not in df.columns:
            return df
        
        # Convert date column to datetime
        try:
            df_copy = df.copy()
            df_copy[date_column] = pd.to_datetime(df_copy[date_column], errors='coerce')
            
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
        """Parse duration string (e.g., '12:34' or '1:23:45') to seconds"""
        if not duration_str or not isinstance(duration_str, str):
            return 0
        
        parts = duration_str.strip().split(':')
        if len(parts) == 2:  # MM:SS
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        else:
            return 0


class CacheManager:
    """Simple in-memory cache for API responses"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Initialize cache manager
        
        Args:
            max_size: Maximum number of cached items
            ttl: Time to live in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache = {}
        self._timestamps = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Any:
        """Get item from cache"""
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
        """Set item in cache"""
        with self._lock:
            # Remove oldest items if cache is full
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._timestamps.keys(), key=lambda k: self._timestamps[k])
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
            
            self._cache[key] = value
            self._timestamps[key] = time.time()
    
    def clear(self):
        """Clear all cached items"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)