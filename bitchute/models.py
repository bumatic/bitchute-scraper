"""
BitChute Scraper Data Models
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Video:
    """Video data model with comprehensive fields"""
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
    hashtags: List[str] = field(default_factory=list)
    category: str = ""
    sensitivity: str = ""
    is_short: bool = False
    scrape_timestamp: float = 0.0
    
    def __post_init__(self):
        """Initialize computed fields"""
        if not self.scrape_timestamp:
            self.scrape_timestamp = datetime.utcnow().timestamp()
        
        if not self.video_url and self.id:
            self.video_url = f"https://www.bitchute.com/video/{self.id}/"
    
    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate (likes + dislikes) / views"""
        if self.view_count == 0:
            return 0.0
        return (self.like_count + self.dislike_count) / self.view_count
    
    @property
    def like_ratio(self) -> float:
        """Calculate like ratio: likes / (likes + dislikes)"""
        total_reactions = self.like_count + self.dislike_count
        if total_reactions == 0:
            return 0.0
        return self.like_count / total_reactions
    
    @property
    def duration_seconds(self) -> int:
        """Convert duration string to seconds"""
        if not self.duration:
            return 0
        
        try:
            parts = self.duration.split(':')
            if len(parts) == 2:  # MM:SS
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
        except (ValueError, AttributeError):
            pass
        
        return 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary with computed properties"""
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'dislike_count': self.dislike_count,
            'duration': self.duration,
            'duration_seconds': self.duration_seconds,
            'channel_id': self.channel_id,
            'channel_name': self.channel_name,
            'upload_date': self.upload_date,
            'thumbnail_url': self.thumbnail_url,
            'video_url': self.video_url,
            'media_url': self.media_url,
            'hashtags': self.hashtags,
            'category': self.category,
            'sensitivity': self.sensitivity,
            'is_short': self.is_short,
            'engagement_rate': self.engagement_rate,
            'like_ratio': self.like_ratio,
            'scrape_timestamp': self.scrape_timestamp
        }
        return data


@dataclass
class Channel:
    """Channel data model"""
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
    scrape_timestamp: float = 0.0
    
    def __post_init__(self):
        """Initialize computed fields"""
        if not self.scrape_timestamp:
            self.scrape_timestamp = datetime.utcnow().timestamp()
        
        if not self.channel_url and self.id:
            self.channel_url = f"https://www.bitchute.com/channel/{self.id}/"
    
    @property
    def subscriber_count_numeric(self) -> int:
        """Convert subscriber count string to numeric value"""
        if not self.subscriber_count:
            return 0
        
        # Handle formats like "1.2K", "500", "2.5M"
        count_str = str(self.subscriber_count).upper().strip()
        
        try:
            if 'K' in count_str:
                return int(float(count_str.replace('K', '')) * 1000)
            elif 'M' in count_str:
                return int(float(count_str.replace('M', '')) * 1000000)
            else:
                return int(float(count_str))
        except (ValueError, AttributeError):
            return 0
    
    @property
    def average_views_per_video(self) -> float:
        """Calculate average views per video"""
        if self.video_count == 0:
            return 0.0
        return self.view_count / self.video_count
    
    def to_dict(self) -> dict:
        """Convert to dictionary with computed properties"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'video_count': self.video_count,
            'subscriber_count': self.subscriber_count,
            'subscriber_count_numeric': self.subscriber_count_numeric,
            'view_count': self.view_count,
            'average_views_per_video': self.average_views_per_video,
            'created_date': self.created_date,
            'category': self.category,
            'thumbnail_url': self.thumbnail_url,
            'channel_url': self.channel_url,
            'is_verified': self.is_verified,
            'scrape_timestamp': self.scrape_timestamp
        }


@dataclass
class Hashtag:
    """Hashtag data model"""
    name: str = ""
    url: str = ""
    rank: int = 0
    video_count: Optional[int] = None
    scrape_timestamp: float = 0.0
    
    def __post_init__(self):
        """Initialize computed fields"""
        if not self.scrape_timestamp:
            self.scrape_timestamp = datetime.utcnow().timestamp()
        
        if not self.url and self.name:
            clean_name = self.name.lstrip('#')
            self.url = f"https://www.bitchute.com/hashtag/{clean_name}/"
    
    @property
    def clean_name(self) -> str:
        """Get hashtag name without # prefix"""
        return self.name.lstrip('#') if self.name else ""
    
    @property
    def formatted_name(self) -> str:
        """Get hashtag name with # prefix"""
        if not self.name:
            return ""
        return f"#{self.clean_name}" if not self.name.startswith('#') else self.name
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'clean_name': self.clean_name,
            'formatted_name': self.formatted_name,
            'url': self.url,
            'rank': self.rank,
            'video_count': self.video_count,
            'scrape_timestamp': self.scrape_timestamp
        }


@dataclass
class SearchResult:
    """Search result container"""
    query: str = ""
    total_results: int = 0
    results_per_page: int = 0
    current_page: int = 0
    videos: List[Video] = field(default_factory=list)
    channels: List[Channel] = field(default_factory=list)
    search_timestamp: float = 0.0
    
    def __post_init__(self):
        """Initialize timestamp"""
        if not self.search_timestamp:
            self.search_timestamp = datetime.utcnow().timestamp()
    
    @property
    def has_results(self) -> bool:
        """Check if search returned any results"""
        return len(self.videos) > 0 or len(self.channels) > 0
    
    @property
    def video_count(self) -> int:
        """Number of videos in results"""
        return len(self.videos)
    
    @property
    def channel_count(self) -> int:
        """Number of channels in results"""
        return len(self.channels)


@dataclass
class APIStats:
    """API usage statistics"""
    requests_made: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cache_hits: int = 0
    total_videos_scraped: int = 0
    total_channels_scraped: int = 0
    total_hashtags_scraped: int = 0
    session_start_time: float = 0.0
    last_request_time: float = 0.0
    
    def __post_init__(self):
        """Initialize timestamps"""
        if not self.session_start_time:
            self.session_start_time = datetime.utcnow().timestamp()
    
    @property
    def success_rate(self) -> float:
        """Calculate request success rate"""
        if self.requests_made == 0:
            return 0.0
        return self.successful_requests / self.requests_made
    
    @property
    def error_rate(self) -> float:
        """Calculate request error rate"""
        if self.requests_made == 0:
            return 0.0
        return self.failed_requests / self.requests_made
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_attempts = self.requests_made + self.cache_hits
        if total_attempts == 0:
            return 0.0
        return self.cache_hits / total_attempts
    
    @property
    def session_duration(self) -> float:
        """Session duration in seconds"""
        current_time = self.last_request_time if self.last_request_time else datetime.utcnow().timestamp()
        return current_time - self.session_start_time
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'requests_made': self.requests_made,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'cache_hits': self.cache_hits,
            'total_videos_scraped': self.total_videos_scraped,
            'total_channels_scraped': self.total_channels_scraped,
            'total_hashtags_scraped': self.total_hashtags_scraped,
            'success_rate': self.success_rate,
            'error_rate': self.error_rate,
            'cache_hit_rate': self.cache_hit_rate,
            'session_duration': self.session_duration,
            'session_start_time': self.session_start_time,
            'last_request_time': self.last_request_time
        }