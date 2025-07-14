"""
BitChute Scraper Utilities Module
"""

import time
import logging
import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import asdict
from datetime import datetime
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
            # Map video_id to id
            video.id = self._safe_get(data, 'video_id', '')
            
            # Map video_name to title
            video.title = self._safe_get(data, 'video_name', '')
            
            # Description
            video.description = self._safe_get(data, 'description', '')
            
            # View count
            video.view_count = self._safe_int(data.get('view_count', 0))
            
            # Duration
            video.duration = self._safe_get(data, 'duration', '')
            
            # Map date_published to upload_date
            video.upload_date = self._safe_get(data, 'date_published', '')
            
            # Thumbnail
            video.thumbnail_url = self._safe_get(data, 'thumbnail_url', '')
            
            # Category (if present)
            video.category = self._safe_get(data, 'category', '')
            
            # Map sensitivity_id to sensitivity
            video.sensitivity = self._safe_get(data, 'sensitivity_id', '')
            
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
            
            # Hashtags processing
            hashtags = data.get('hashtags', data.get('tags', []))
            if isinstance(hashtags, list):
                video.hashtags = [
                    f"#{tag}" if not str(tag).startswith('#') else str(tag) 
                    for tag in hashtags if tag
                ]
            
            # Engagement metrics (may be populated later)
            video.like_count = self._safe_int(data.get('like_count', 0))
            video.dislike_count = self._safe_int(data.get('dislike_count', 0))
            
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
            
            # Media URL if present
            video.media_url = self._safe_get(data, 'media_url', '')
            
            # Additional fields that might be useful (store in description or create new fields)
            # state_id could be useful for filtering published vs unpublished videos
            state_id = self._safe_get(data, 'state_id', '')
            
        except Exception as e:
            logger.warning(f"Error parsing video data: {e}")
        
        return video
    
    def parse_channel(self, data: Dict[str, Any], rank: int = 0) -> Channel:
        """
        Parse channel data from API response with correct field mapping
        
        Args:
            data: Raw channel data from API
            rank: Channel ranking/position
            
        Returns:
            Parsed Channel object
        """
        channel = Channel()
        
        try:
            # Map channel_id to id
            channel.id = self._safe_get(data, 'channel_id', self._safe_get(data, 'id', ''))
            
            # Map channel_name to name
            channel.name = self._safe_get(data, 'channel_name', self._safe_get(data, 'name', data.get('title', '')))
            
            # Description
            channel.description = self._safe_get(data, 'description', '')
            
            # Stats
            channel.video_count = self._safe_int(data.get('video_count', 0))
            channel.subscriber_count = str(data.get('subscriber_count', ''))
            channel.view_count = self._safe_int(data.get('view_count', 0))
            
            # Dates
            channel.created_date = self._safe_get(data, 'created_at', data.get('date_created', ''))
            
            # Category
            channel.category = self._safe_get(data, 'category', '')
            
            # Thumbnail
            channel.thumbnail_url = self._safe_get(data, 'thumbnail_url', '')
            
            # Verification status
            channel.is_verified = bool(data.get('is_verified', False))
            
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
            hashtag.name = self._safe_get(data, 'name', '')
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
        """
        Get multiple pages of data from an API method
        
        Args:
            api_method: API method to call
            max_pages: Maximum pages to retrieve
            per_page: Items per page
            **kwargs: Additional arguments for API method
            
        Returns:
            Combined DataFrame from all pages
        """
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
                    break
                
                all_data.append(df)
                
                logger.info(f"Page {page + 1}: {len(df)} items")
                
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
        Get details for multiple videos concurrently
        
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


class DataAnalyzer:
    """Analyze and summarize scraped data"""
    
    @staticmethod
    def analyze_videos(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze video data and return insights
        
        Args:
            df: DataFrame with video data
            
        Returns:
            Dictionary with analysis results
        """
        if df.empty:
            return {'error': 'No data to analyze'}
        
        analysis = {
            'total_videos': len(df),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # View count analysis
        if 'view_count' in df.columns:
            view_counts = df['view_count'].dropna()
            if not view_counts.empty:
                analysis['views'] = {
                    'total': int(view_counts.sum()),
                    'average': float(view_counts.mean()),
                    'median': float(view_counts.median()),
                    'max': int(view_counts.max()),
                    'min': int(view_counts.min())
                }
        
        # Channel analysis
        if 'channel_name' in df.columns:
            channel_counts = df['channel_name'].value_counts()
            analysis['top_channels'] = channel_counts.head(10).to_dict()
            analysis['unique_channels'] = len(channel_counts)
        
        # Category analysis
        if 'category' in df.columns:
            category_counts = df['category'].value_counts()
            analysis['categories'] = category_counts.to_dict()
        
        # Duration analysis
        if 'duration' in df.columns:
            durations = df['duration'].dropna()
            if not durations.empty:
                # Convert duration strings to seconds for analysis
                duration_seconds = []
                for duration in durations:
                    try:
                        seconds = DataAnalyzer._parse_duration(duration)
                        if seconds > 0:
                            duration_seconds.append(seconds)
                    except:
                        continue
                
                if duration_seconds:
                    analysis['duration'] = {
                        'average_seconds': float(sum(duration_seconds) / len(duration_seconds)),
                        'average_minutes': float(sum(duration_seconds) / len(duration_seconds) / 60),
                        'max_seconds': max(duration_seconds),
                        'min_seconds': min(duration_seconds)
                    }
        
        # Hashtag analysis
        if 'hashtags' in df.columns:
            all_hashtags = []
            for hashtag_list in df['hashtags'].dropna():
                if isinstance(hashtag_list, list):
                    all_hashtags.extend(hashtag_list)
                elif isinstance(hashtag_list, str):
                    # Handle string representation of lists
                    try:
                        import ast
                        hashtag_list = ast.literal_eval(hashtag_list)
                        if isinstance(hashtag_list, list):
                            all_hashtags.extend(hashtag_list)
                    except:
                        pass
            
            if all_hashtags:
                from collections import Counter
                hashtag_counts = Counter(all_hashtags)
                analysis['top_hashtags'] = dict(hashtag_counts.most_common(20))
        
        return analysis
    
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
                return DataAnalyzer._parse_duration(duration_str)
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