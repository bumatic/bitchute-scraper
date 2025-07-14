# BitChute API Scraper - Modern Implementation
# Copyright (c) 2025 Marcus Burkhardt
# Complete rewrite using BitChute's official API endpoints

import time
import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import concurrent.futures
import threading

import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from retrying import retry

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class Video:
    """Video data structure"""
    id: str = ""
    title: str = ""
    description: str = ""
    view_count: int = 0
    like_count: int = 0
    dislike_count: int = 0
    duration: str = ""
    channel_id: str = ""
    channel_name: str = ""
    upload_date: str = ""
    thumbnail_url: str = ""
    video_url: str = ""
    media_url: str = ""
    hashtags: List[str] = None
    category: str = ""
    sensitivity: str = ""
    is_short: bool = False
    scrape_timestamp: float = 0

    def __post_init__(self):
        if self.hashtags is None:
            self.hashtags = []
        if not self.scrape_timestamp:
            self.scrape_timestamp = datetime.utcnow().timestamp()
        if not self.video_url and self.id:
            self.video_url = f"https://www.bitchute.com/video/{self.id}/"


@dataclass
class Channel:
    """Channel data structure"""
    id: str = ""
    name: str = ""
    description: str = ""
    video_count: int = 0
    subscriber_count: str = ""
    view_count: int = 0
    created_date: str = ""
    category: str = ""
    thumbnail_url: str = ""
    channel_url: str = ""
    is_verified: bool = False
    scrape_timestamp: float = 0

    def __post_init__(self):
        if not self.scrape_timestamp:
            self.scrape_timestamp = datetime.utcnow().timestamp()
        if not self.channel_url and self.id:
            self.channel_url = f"https://www.bitchute.com/channel/{self.id}/"


@dataclass
class Hashtag:
    """Hashtag data structure"""
    name: str = ""
    url: str = ""
    rank: int = 0
    scrape_timestamp: float = 0

    def __post_init__(self):
        if not self.scrape_timestamp:
            self.scrape_timestamp = datetime.utcnow().timestamp()
        if not self.url and self.name:
            clean_name = self.name.lstrip('#')
            self.url = f"https://www.bitchute.com/hashtag/{clean_name}/"


class TokenManager:
    """Manages BitChute API authentication tokens"""
    
    def __init__(self, cache_tokens: bool = True, verbose: bool = False):
        self.cache_tokens = cache_tokens
        self.verbose = verbose
        self.token = None
        self.expires_at = 0
        self.cache_file = Path.home() / '.bitchute_api_token.json'
        self.webdriver = None
        
        if cache_tokens:
            self._load_cached_token()
    
    def _load_cached_token(self):
        """Load token from cache if valid"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                
                # Check if token is still valid (30 min buffer)
                if data.get('expires_at', 0) > time.time() + 1800:
                    self.token = data.get('token')
                    self.expires_at = data.get('expires_at', 0)
                    
                    if self.verbose:
                        logger.info("Loaded cached API token")
        except Exception as e:
            if self.verbose:
                logger.warning(f"Failed to load cached token: {e}")
    
    def _save_token_cache(self):
        """Save token to cache"""
        if not self.cache_tokens or not self.token:
            return
        
        try:
            data = {
                'token': self.token,
                'expires_at': self.expires_at,
                'created_at': time.time()
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(data, f)
                
            if self.verbose:
                logger.info("Saved API token to cache")
        except Exception as e:
            if self.verbose:
                logger.warning(f"Failed to save token cache: {e}")
    
    def _create_webdriver(self):
        """Create minimal webdriver for token extraction"""
        if self.webdriver:
            return
        
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-gpu')
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        try:
            self.webdriver = webdriver.Chrome(
                service=webdriver.ChromeService(ChromeDriverManager().install()),
                options=options
            )
            self.webdriver.set_page_load_timeout(30)
        except Exception as e:
            if self.verbose:
                logger.error(f"Failed to create webdriver: {e}")
            raise
    
    def _close_webdriver(self):
        """Close webdriver"""
        if self.webdriver:
            try:
                self.webdriver.quit()
            except Exception:
                pass
            finally:
                self.webdriver = None
    
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def _extract_token(self) -> Optional[str]:
        """Extract service token from BitChute"""
        try:
            if self.verbose:
                logger.info("Extracting API token from BitChute")
            
            self._create_webdriver()
            self.webdriver.get('https://www.bitchute.com/')
            
            # Wait for page load
            WebDriverWait(self.webdriver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Extract token from page source
            page_source = self.webdriver.page_source
            
            # Look for token patterns
            patterns = [
                r'"x-service-info":\s*"([^"]+)"',
                r'x-service-info["\']:\s*["\']([^"\']+)["\']',
                r'serviceInfo["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    token = match.group(1)
                    if len(token) > 10:
                        if self.verbose:
                            logger.info(f"Extracted token: {token[:12]}...")
                        return token
            
            if self.verbose:
                logger.warning("Could not extract API token")
            return None
            
        except Exception as e:
            if self.verbose:
                logger.error(f"Token extraction failed: {e}")
            return None
        finally:
            self._close_webdriver()
    
    def get_token(self) -> Optional[str]:
        """Get valid API token"""
        # Check if current token is still valid
        if self.token and time.time() < self.expires_at - 1800:  # 30 min buffer
            return self.token
        
        # Extract new token
        token = self._extract_token()
        if token:
            self.token = token
            self.expires_at = time.time() + 3600  # 1 hour expiry
            
            if self.cache_tokens:
                self._save_token_cache()
        
        return self.token
    
    def __del__(self):
        """Cleanup"""
        self._close_webdriver()


class BitChuteAPI:
    """Modern BitChute API client"""
    
    def __init__(self, verbose: bool = False, cache_tokens: bool = True):
        self.verbose = verbose
        self.token_manager = TokenManager(cache_tokens, verbose)
        
        # Configure logging
        if verbose:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.WARNING)
            logging.getLogger('selenium').setLevel(logging.WARNING)
            logging.getLogger('urllib3').setLevel(logging.WARNING)
            logging.getLogger('WDM').setLevel(logging.WARNING)
        
        # API configuration
        self.base_url = "https://api.bitchute.com/api"
        self.rate_limit = 0.5  # seconds between requests
        self.last_request = 0
        
        # Setup requests session
        self.session = requests.Session()
        self.session.headers.update({
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://www.bitchute.com',
            'referer': 'https://www.bitchute.com/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        })
    
    def _rate_limit(self):
        """Apply rate limiting"""
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()
    
    def _make_request(self, endpoint: str, payload: dict, require_token: bool = True) -> Optional[dict]:
        """Make API request"""
        self._rate_limit()
        
        # Get token if required
        if require_token:
            token = self.token_manager.get_token()
            if token:
                self.session.headers['x-service-info'] = token
            elif self.verbose:
                logger.warning(f"No token available for {endpoint}")
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if self.verbose:
                logger.info(f"API: {endpoint}")
            
            response = self.session.post(url, json=payload, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [401, 403] and require_token:
                # Token might be invalid, try refresh once
                self.token_manager.token = None
                token = self.token_manager.get_token()
                if token:
                    self.session.headers['x-service-info'] = token
                    response = self.session.post(url, json=payload, timeout=15)
                    if response.status_code == 200:
                        return response.json()
            
            if self.verbose:
                logger.warning(f"API error: {endpoint} - {response.status_code}")
            return None
            
        except Exception as e:
            if self.verbose:
                logger.error(f"Request failed: {endpoint} - {e}")
            return None
    
    def _parse_video(self, data: dict, rank: int = 0) -> Video:
        """Parse video data from API response"""
        video = Video()
        
        try:
            video.id = data.get('id', '')
            video.title = data.get('title', '')
            video.description = data.get('description', '')
            video.view_count = int(data.get('view_count', 0) or 0)
            video.duration = data.get('duration', '')
            video.upload_date = data.get('upload_date', data.get('created_at', ''))
            video.thumbnail_url = data.get('thumbnail_url', '')
            video.category = data.get('category', '')
            video.sensitivity = data.get('sensitivity', '')
            video.is_short = data.get('is_short', False)
            
            # Channel info
            uploader = data.get('uploader', {})
            if isinstance(uploader, dict):
                video.channel_id = uploader.get('id', '')
                video.channel_name = uploader.get('name', '')
            
            # Hashtags
            hashtags = data.get('hashtags', [])
            if isinstance(hashtags, list):
                video.hashtags = [f"#{tag}" if not tag.startswith('#') else tag for tag in hashtags]
            
        except Exception as e:
            if self.verbose:
                logger.warning(f"Error parsing video: {e}")
        
        return video
    
    def _parse_channel(self, data: dict, rank: int = 0) -> Channel:
        """Parse channel data from API response"""
        channel = Channel()
        
        try:
            channel.id = data.get('id', '')
            channel.name = data.get('name', data.get('title', ''))
            channel.description = data.get('description', '')
            channel.video_count = int(data.get('video_count', 0) or 0)
            channel.subscriber_count = str(data.get('subscriber_count', ''))
            channel.view_count = int(data.get('view_count', 0) or 0)
            channel.created_date = data.get('created_at', '')
            channel.category = data.get('category', '')
            channel.thumbnail_url = data.get('thumbnail_url', '')
            channel.is_verified = data.get('is_verified', False)
            
        except Exception as e:
            if self.verbose:
                logger.warning(f"Error parsing channel: {e}")
        
        return channel
    
    def get_trending_videos(self, timeframe: str = 'day', limit: int = 20) -> pd.DataFrame:
        """Get trending videos"""
        selection_map = {
            'day': 'trending-day',
            'week': 'trending-week',
            'month': 'trending-month'
        }
        
        selection = selection_map.get(timeframe, 'trending-day')
        payload = {
            "selection": selection,
            "offset": 0,
            "limit": limit,
            "advertisable": True
        }
        
        data = self._make_request("beta/videos", payload)
        if not data or 'videos' not in data:
            return pd.DataFrame()
        
        videos = []
        for i, video_data in enumerate(data['videos'], 1):
            video = self._parse_video(video_data, i)
            videos.append(asdict(video))
        
        df = pd.DataFrame(videos)
        
        if self.verbose:
            logger.info(f"Retrieved {len(videos)} trending videos ({timeframe})")
        
        return df
    
    def get_popular_videos(self, limit: int = 30) -> pd.DataFrame:
        """Get popular videos"""
        payload = {
            "selection": "popular",
            "offset": 0,
            "limit": limit,
            "advertisable": True
        }
        
        data = self._make_request("beta/videos", payload)
        if not data or 'videos' not in data:
            return pd.DataFrame()
        
        videos = []
        for i, video_data in enumerate(data['videos'], 1):
            video = self._parse_video(video_data, i)
            videos.append(asdict(video))
        
        df = pd.DataFrame(videos)
        
        if self.verbose:
            logger.info(f"Retrieved {len(videos)} popular videos")
        
        return df
    
    def get_recent_videos(self, limit: int = 30, offset: int = 0) -> pd.DataFrame:
        """Get recent videos"""
        payload = {
            "selection": "all",
            "offset": offset,
            "limit": limit,
            "advertisable": True
        }
        
        data = self._make_request("beta/videos", payload)
        if not data or 'videos' not in data:
            return pd.DataFrame()
        
        videos = []
        for i, video_data in enumerate(data['videos'], 1):
            video = self._parse_video(video_data, offset + i)
            videos.append(asdict(video))
        
        df = pd.DataFrame(videos)
        
        if self.verbose:
            logger.info(f"Retrieved {len(videos)} recent videos")
        
        return df
    
    def get_shorts(self, limit: int = 50, offset: int = 0) -> pd.DataFrame:
        """Get short videos"""
        payload = {
            "selection": "all",
            "offset": offset,
            "limit": limit,
            "advertisable": True,
            "is_short": True
        }
        
        data = self._make_request("beta/videos", payload)
        if not data or 'videos' not in data:
            return pd.DataFrame()
        
        videos = []
        for i, video_data in enumerate(data['videos'], 1):
            video = self._parse_video(video_data, offset + i)
            videos.append(asdict(video))
        
        df = pd.DataFrame(videos)
        
        if self.verbose:
            logger.info(f"Retrieved {len(videos)} shorts")
        
        return df
    
    def get_member_picked(self, limit: int = 24) -> pd.DataFrame:
        """Get member picked videos"""
        payload = {"limit": limit}
        
        data = self._make_request("beta/member_liked_videos", payload)
        if not data or 'videos' not in data:
            return pd.DataFrame()
        
        videos = []
        for i, video_data in enumerate(data['videos'], 1):
            video = self._parse_video(video_data, i)
            videos.append(asdict(video))
        
        df = pd.DataFrame(videos)
        
        if self.verbose:
            logger.info(f"Retrieved {len(videos)} member picked videos")
        
        return df
    
    def search_videos(self, query: str, sensitivity: str = "normal", sort: str = "new",
                     limit: int = 50, offset: int = 0) -> pd.DataFrame:
        """Search for videos"""
        payload = {
            "offset": offset,
            "limit": limit,
            "query": query,
            "sensitivity_id": sensitivity,  # normal, nsfw, nsfl
            "sort": sort  # new, relevant, views
        }
        
        data = self._make_request("beta/search/videos", payload)
        if not data or 'videos' not in data:
            return pd.DataFrame()
        
        videos = []
        for i, video_data in enumerate(data['videos'], 1):
            video = self._parse_video(video_data, offset + i)
            videos.append(asdict(video))
        
        df = pd.DataFrame(videos)
        
        if self.verbose:
            logger.info(f"Found {len(videos)} videos for '{query}'")
        
        return df
    
    def search_channels(self, query: str, sensitivity: str = "normal",
                       limit: int = 50, offset: int = 0) -> pd.DataFrame:
        """Search for channels"""
        payload = {
            "offset": offset,
            "limit": limit,
            "query": query,
            "sensitivity_id": sensitivity
        }
        
        data = self._make_request("beta/search/channels", payload)
        if not data or 'channels' not in data:
            return pd.DataFrame()
        
        channels = []
        for i, channel_data in enumerate(data['channels'], 1):
            channel = self._parse_channel(channel_data, offset + i)
            channels.append(asdict(channel))
        
        df = pd.DataFrame(channels)
        
        if self.verbose:
            logger.info(f"Found {len(channels)} channels for '{query}'")
        
        return df
    
    def get_trending_hashtags(self, limit: int = 50, offset: int = 0) -> pd.DataFrame:
        """Get trending hashtags"""
        payload = {
            "offset": offset,
            "limit": limit
        }
        
        data = self._make_request("beta9/hashtag/trending/", payload, require_token=False)
        if not data or 'hashtags' not in data:
            return pd.DataFrame()
        
        hashtags = []
        for i, tag_data in enumerate(data['hashtags'], 1):
            hashtag = Hashtag()
            hashtag.name = tag_data.get('name', '')
            hashtag.rank = offset + i
            hashtags.append(asdict(hashtag))
        
        df = pd.DataFrame(hashtags)
        
        if self.verbose:
            logger.info(f"Retrieved {len(hashtags)} trending hashtags")
        
        return df
    
    def get_video_details(self, video_id: str, include_counts: bool = True, 
                         include_media: bool = False) -> Optional[Video]:
        """Get detailed video information"""
        payload = {"video_id": video_id}
        
        # Get basic video data
        data = self._make_request("beta9/video", payload, require_token=False)
        if not data:
            return None
        
        video = self._parse_video(data)
        
        # Get like/dislike counts
        if include_counts:
            counts_data = self._make_request("beta/video/counts", payload)
            if counts_data:
                video.like_count = int(counts_data.get('like_count', 0) or 0)
                video.dislike_count = int(counts_data.get('dislike_count', 0) or 0)
        
        # Get media URL
        if include_media:
            media_data = self._make_request("beta/video/media", payload)
            if media_data:
                video.media_url = media_data.get('media_url', '')
        
        return video
    
    def get_multiple_pages(self, method_name: str, max_pages: int = 5, 
                          per_page: int = 50, **kwargs) -> pd.DataFrame:
        """Get multiple pages of data"""
        all_data = []
        method = getattr(self, method_name)
        
        for page in range(max_pages):
            offset = page * per_page
            
            if method_name in ['get_recent_videos', 'get_shorts', 'search_videos', 'search_channels']:
                df = method(limit=per_page, offset=offset, **kwargs)
            else:
                df = method(limit=per_page, **kwargs)
            
            if df.empty:
                break
            
            all_data.append(df)
            
            if self.verbose:
                logger.info(f"Page {page + 1}: {len(df)} items")
            
            time.sleep(0.5)  # Be nice to the API
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        
        return pd.DataFrame()
    
    def bulk_video_details(self, video_ids: List[str], max_workers: int = 5,
                          include_counts: bool = True) -> List[Video]:
        """Get details for multiple videos concurrently"""
        videos = []
        
        def get_video_details_thread(video_id):
            try:
                return self.get_video_details(video_id, include_counts=include_counts)
            except Exception as e:
                if self.verbose:
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
        
        if self.verbose:
            logger.info(f"Retrieved details for {len(videos)}/{len(video_ids)} videos")
        
        return videos
    
    def export_data(self, df: pd.DataFrame, filename: str, 
                   formats: List[str] = None) -> Dict[str, str]:
        """Export data to various formats"""
        if formats is None:
            formats = ['csv']
        
        exported = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for fmt in formats:
            try:
                if fmt == 'csv':
                    filepath = f"{filename}_{timestamp}.csv"
                    df.to_csv(filepath, index=False, encoding='utf-8')
                    exported['csv'] = filepath
                    
                elif fmt == 'json':
                    filepath = f"{filename}_{timestamp}.json"
                    df.to_json(filepath, orient='records', indent=2, force_ascii=False)
                    exported['json'] = filepath
                    
                elif fmt == 'xlsx':
                    filepath = f"{filename}_{timestamp}.xlsx"
                    df.to_excel(filepath, index=False, engine='openpyxl')
                    exported['xlsx'] = filepath
                    
                elif fmt == 'parquet':
                    filepath = f"{filename}_{timestamp}.parquet"
                    df.to_parquet(filepath, index=False)
                    exported['parquet'] = filepath
                
                if self.verbose:
                    logger.info(f"Exported to {filepath}")
                    
            except Exception as e:
                if self.verbose:
                    logger.error(f"Export failed for {fmt}: {e}")
        
        return exported
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token_manager:
            self.token_manager._close_webdriver()
        if hasattr(self, 'session'):
            self.session.close()


# Main usage example
if __name__ == "__main__":
    # Initialize API
    api = BitChuteAPI(verbose=True)
    
    # Get trending videos
    trending = api.get_trending_videos('day', limit=20)
    print(f"Trending videos: {len(trending)}")
    
    if not trending.empty:
        print("\nTop 5 trending:")
        for i, (_, video) in enumerate(trending.head().iterrows(), 1):
            print(f"{i}. {video['title'][:60]}... - {video['view_count']:,} views")
    
    # Search example
    results = api.search_videos('programming', limit=10)
    print(f"\nSearch results: {len(results)} videos")
    
    # Export example
    if not trending.empty:
        exported = api.export_data(trending, 'bitchute_trending', ['csv', 'json'])
        print(f"\nExported: {list(exported.keys())}")