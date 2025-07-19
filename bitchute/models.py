"""
BitChute Scraper Data Models

Comprehensive data models for BitChute platform entities including videos,
channels, hashtags, and search results with computed properties and download support.

This module provides structured data representations for all BitChute platform
entities with automatic field validation, computed properties, and support for
media downloads.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timezone

@dataclass
class Video:
    """Comprehensive video data model with engagement metrics and download support.
    
    Represents a BitChute video with complete metadata, engagement statistics,
    and local file paths for downloaded media. Includes computed properties
    for analysis and data processing.
    
    Attributes:
        id: Unique video identifier
        title: Video title
        description: Video description text
        view_count: Number of video views
        like_count: Number of likes received
        dislike_count: Number of dislikes received
        duration: Video duration string (e.g., "12:34" or "1:23:45")
        thumbnail_url: URL to video thumbnail image
        video_url: URL to video page on BitChute
        media_url: Direct URL to video media file
        media_type: MIME type of video file
        channel_id: Unique identifier of uploading channel
        channel_name: Name of uploading channel
        profile_id: Profile ID of channel owner
        category: Video category name
        category_id: Video category identifier
        sensitivity: Content sensitivity level
        hashtags: List of associated hashtags
        state: Video publication state
        is_short: Whether video is classified as short-form content
        is_liked: Whether current user has liked video
        is_disliked: Whether current user has disliked video
        is_discussable: Whether comments are enabled
        show_comments: Whether comments section is visible
        show_adverts: Whether advertisements are enabled
        show_promo: Whether promotional content is shown
        show_rantrave: Whether rant/rave feature is enabled
        upload_date: ISO format upload timestamp
        scrape_timestamp: Unix timestamp when data was collected
        rumble_id: Associated Rumble platform identifier
        local_thumbnail_path: Local file path to downloaded thumbnail
        local_video_path: Local file path to downloaded video file
    
    Example:
        >>> video = Video()
        >>> video.id = "CLrgZP4RWyly"
        >>> video.title = "Sample Video"
        >>> video.view_count = 1500
        >>> video.like_count = 45
        >>> video.dislike_count = 3
        >>> print(f"Engagement rate: {video.engagement_rate:.2%}")
        >>> print(f"Like ratio: {video.like_ratio:.2%}")
    """
    
    # Core identifiers
    id: str = ""
    title: str = ""
    description: str = ""
    
    # View and engagement metrics
    view_count: int = 0
    like_count: int = 0
    dislike_count: int = 0
    
    # Video properties
    duration: str = ""
    thumbnail_url: str = ""
    video_url: str = ""
    media_url: str = ""
    media_type: str = ""
    
    # Channel information
    channel_id: str = ""
    channel_name: str = ""
    profile_id: str = ""
    
    # Categorization
    category: str = ""
    category_id: str = ""
    sensitivity: str = ""
    hashtags: List[str] = field(default_factory=list)
    
    # Status and flags
    state: str = ""
    is_short: bool = False
    is_liked: bool = False
    is_disliked: bool = False
    is_discussable: bool = True
    
    # Display settings
    show_comments: bool = True
    show_adverts: bool = True
    show_promo: bool = True
    show_rantrave: bool = False
    
    # Timestamps
    upload_date: str = ""
    scrape_timestamp: float = 0.0
    
    # External IDs
    rumble_id: str = ""
    
    # Download-related fields
    local_thumbnail_path: str = ""
    local_video_path: str = ""
    
    def __post_init__(self):
        """Initialize computed fields and set default values.
        
        Sets scrape timestamp to current time if not provided and constructs
        video URL from ID if not already set.
        """
        if not self.scrape_timestamp:
            self.scrape_timestamp = datetime.now(timezone.utc).timestamp()
        
        if not self.video_url and self.id:
            self.video_url = f"https://www.bitchute.com/video/{self.id}/"
    
    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate as proportion of views.
        
        Returns:
            float: Engagement rate calculated as (likes + dislikes) / views.
                Returns 0.0 if view count is zero.
                
        Example:
            >>> video = Video()
            >>> video.view_count = 1000
            >>> video.like_count = 50
            >>> video.dislike_count = 5
            >>> print(f"{video.engagement_rate:.1%}")  # "5.5%"
        """
        if self.view_count == 0:
            return 0.0
        return (self.like_count + self.dislike_count) / self.view_count
    
    @property
    def like_ratio(self) -> float:
        """Calculate like ratio among total reactions.
        
        Returns:
            float: Like ratio calculated as likes / (likes + dislikes).
                Returns 0.0 if no reactions exist.
                
        Example:
            >>> video = Video()
            >>> video.like_count = 80
            >>> video.dislike_count = 20
            >>> print(f"{video.like_ratio:.1%}")  # "80.0%"
        """
        total_reactions = self.like_count + self.dislike_count
        if total_reactions == 0:
            return 0.0
        return self.like_count / total_reactions
    
    @property
    def duration_seconds(self) -> int:
        """Convert duration string to total seconds.
        
        Parses duration strings in MM:SS or HH:MM:SS format and converts
        to total seconds for numerical analysis.
        
        Returns:
            int: Total duration in seconds. Returns 0 if parsing fails.
            
        Example:
            >>> video = Video()
            >>> video.duration = "12:34"
            >>> print(video.duration_seconds)  # 754
            >>> video.duration = "1:23:45"
            >>> print(video.duration_seconds)  # 5025
        """
        if not self.duration:
            return 0
        
        try:
            parts = self.duration.split(':')
            if len(parts) == 2:  # MM:SS format
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS format
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
        except (ValueError, AttributeError):
            pass
        
        return 0
    
    @property
    def has_local_thumbnail(self) -> bool:
        """Check if thumbnail has been downloaded locally.
        
        Returns:
            bool: True if local thumbnail path is set and non-empty.
            
        Example:
            >>> video = Video()
            >>> print(video.has_local_thumbnail)  # False
            >>> video.local_thumbnail_path = "/path/to/thumb.jpg"
            >>> print(video.has_local_thumbnail)  # True
        """
        return bool(self.local_thumbnail_path and self.local_thumbnail_path.strip())
    
    @property
    def has_local_video(self) -> bool:
        """Check if video file has been downloaded locally.
        
        Returns:
            bool: True if local video path is set and non-empty.
            
        Example:
            >>> video = Video()
            >>> print(video.has_local_video)  # False
            >>> video.local_video_path = "/path/to/video.mp4"
            >>> print(video.has_local_video)  # True
        """
        return bool(self.local_video_path and self.local_video_path.strip())
    
    @property
    def is_fully_downloaded(self) -> bool:
        """Check if both thumbnail and video are downloaded locally.
        
        Returns:
            bool: True if both thumbnail and video files are available locally.
            
        Example:
            >>> video = Video()
            >>> video.local_thumbnail_path = "/path/to/thumb.jpg"
            >>> video.local_video_path = "/path/to/video.mp4"
            >>> print(video.is_fully_downloaded)  # True
        """
        return self.has_local_thumbnail and self.has_local_video
    
    def to_dict(self) -> dict:
        """Convert video object to dictionary with computed properties.
        
        Creates a comprehensive dictionary representation including all
        fields and computed properties for serialization or analysis.
        
        Returns:
            dict: Dictionary containing all video data and computed properties.
            
        Example:
            >>> video = Video()
            >>> video.id = "test123"
            >>> video.view_count = 1000
            >>> data = video.to_dict()
            >>> print(data['engagement_rate'])
        """
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
            'profile_id': self.profile_id,
            'upload_date': self.upload_date,
            'thumbnail_url': self.thumbnail_url,
            'video_url': self.video_url,
            'media_url': self.media_url,
            'media_type': self.media_type,
            'hashtags': self.hashtags,
            'category': self.category,
            'category_id': self.category_id,
            'sensitivity': self.sensitivity,
            'state': self.state,
            'is_short': self.is_short,
            'is_liked': self.is_liked,
            'is_disliked': self.is_disliked,
            'is_discussable': self.is_discussable,
            'show_comments': self.show_comments,
            'show_adverts': self.show_adverts,
            'show_promo': self.show_promo,
            'show_rantrave': self.show_rantrave,
            'engagement_rate': self.engagement_rate,
            'like_ratio': self.like_ratio,
            'rumble_id': self.rumble_id,
            'scrape_timestamp': self.scrape_timestamp,
            'local_thumbnail_path': self.local_thumbnail_path,
            'local_video_path': self.local_video_path,
            'has_local_thumbnail': self.has_local_thumbnail,
            'has_local_video': self.has_local_video,
            'is_fully_downloaded': self.is_fully_downloaded
        }
        return data

@dataclass
class Channel:
    """Comprehensive channel data model with statistics and social links.
    
    Represents a BitChute channel with complete metadata, statistics,
    and configuration settings. Includes computed properties for analytics
    and social media link tracking.
    
    Attributes:
        id: Unique channel identifier
        name: Channel display name
        description: Channel description text
        url_slug: URL-friendly channel identifier
        video_count: Total number of uploaded videos
        subscriber_count: Subscriber count (may be formatted string)
        view_count: Total views across all videos
        created_date: Channel creation date
        last_video_published: Date of most recent video upload
        profile_id: Associated profile identifier
        profile_name: Profile display name
        category: Channel category name
        category_id: Channel category identifier
        sensitivity: Content sensitivity level
        sensitivity_id: Sensitivity level identifier
        thumbnail_url: Channel thumbnail/avatar URL
        channel_url: Full URL to channel page
        state: Channel status/state
        state_id: Channel state identifier
        membership_level: Channel membership tier
        is_verified: Whether channel is verified
        is_subscribed: Whether current user is subscribed
        is_notified: Whether notifications are enabled
        show_adverts: Whether advertisements are enabled
        show_comments: Whether comments are enabled
        show_rantrave: Whether rant/rave feature is enabled
        live_stream_enabled: Whether live streaming is available
        feature_video: Featured video identifier
        scrape_timestamp: Unix timestamp when data was collected
        social_links: List of social media links (populated by API)
    
    Example:
        >>> channel = Channel()
        >>> channel.id = "test_channel"
        >>> channel.name = "Test Channel"
        >>> channel.subscriber_count = "1.2K"
        >>> channel.video_count = 150
        >>> channel.view_count = 500000
        >>> print(f"Numeric subscribers: {channel.subscriber_count_numeric}")
        >>> print(f"Avg views per video: {channel.average_views_per_video:.0f}")
    """
    
    # Core identifiers
    id: str = ""
    name: str = ""
    description: str = ""
    url_slug: str = ""
    
    # Statistics
    video_count: int = 0
    subscriber_count: str = ""
    view_count: int = 0
    
    # Dates
    created_date: str = ""
    last_video_published: str = ""
    
    # Profile information
    profile_id: str = ""
    profile_name: str = ""
    
    # Categorization
    category: str = ""
    category_id: str = ""
    sensitivity: str = ""
    sensitivity_id: str = ""
    
    # URLs
    thumbnail_url: str = ""
    channel_url: str = ""
    
    # Status and settings
    state: str = ""
    state_id: str = ""
    membership_level: str = "Default"
    is_verified: bool = False
    is_subscribed: bool = False
    is_notified: bool = False
    
    # Display settings
    show_adverts: bool = True
    show_comments: bool = True
    show_rantrave: bool = True
    
    # Features
    live_stream_enabled: bool = False
    feature_video: Optional[str] = None
    
    # Metadata
    scrape_timestamp: float = 0.0
    
    # Social media links (populated by API)
    social_links: List[dict] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize computed fields and set default values.
        
        Sets scrape timestamp to current time if not provided and constructs
        channel URL from ID if not already set.
        """
        if not self.scrape_timestamp:
            self.scrape_timestamp = datetime.now(timezone.utc).timestamp()
        
        if not self.channel_url and self.id:
            self.channel_url = f"https://www.bitchute.com/channel/{self.id}/"
    
    @property
    def subscriber_count_numeric(self) -> int:
        """Convert formatted subscriber count to numeric value.
        
        Parses subscriber count strings with K/M suffixes and converts
        to numeric values for analysis and sorting.
        
        Returns:
            int: Numeric subscriber count. Returns 0 if parsing fails.
            
        Example:
            >>> channel = Channel()
            >>> channel.subscriber_count = "1.2K"
            >>> print(channel.subscriber_count_numeric)  # 1200
            >>> channel.subscriber_count = "2.5M"
            >>> print(channel.subscriber_count_numeric)  # 2500000
        """
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
        """Calculate average views per video across channel.
        
        Returns:
            float: Average view count per video. Returns 0.0 if no videos exist.
            
        Example:
            >>> channel = Channel()
            >>> channel.view_count = 100000
            >>> channel.video_count = 50
            >>> print(channel.average_views_per_video)  # 2000.0
        """
        if self.video_count == 0:
            return 0.0
        return self.view_count / self.video_count
    
    def to_dict(self) -> dict:
        """Convert channel object to dictionary with computed properties.
        
        Creates a comprehensive dictionary representation including all
        fields and computed properties for serialization or analysis.
        
        Returns:
            dict: Dictionary containing all channel data and computed properties.
            
        Example:
            >>> channel = Channel()
            >>> channel.id = "test123"
            >>> channel.subscriber_count = "5.5K"
            >>> data = channel.to_dict()
            >>> print(data['subscriber_count_numeric'])  # 5500
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'url_slug': self.url_slug,
            'video_count': self.video_count,
            'subscriber_count': self.subscriber_count,
            'subscriber_count_numeric': self.subscriber_count_numeric,
            'view_count': self.view_count,
            'average_views_per_video': self.average_views_per_video,
            'created_date': self.created_date,
            'last_video_published': self.last_video_published,
            'profile_id': self.profile_id,
            'profile_name': self.profile_name,
            'category': self.category,
            'category_id': self.category_id,
            'sensitivity': self.sensitivity,
            'sensitivity_id': self.sensitivity_id,
            'thumbnail_url': self.thumbnail_url,
            'channel_url': self.channel_url,
            'state': self.state,
            'state_id': self.state_id,
            'membership_level': self.membership_level,
            'is_verified': self.is_verified,
            'is_subscribed': self.is_subscribed,
            'is_notified': self.is_notified,
            'show_adverts': self.show_adverts,
            'show_comments': self.show_comments,
            'show_rantrave': self.show_rantrave,
            'live_stream_enabled': self.live_stream_enabled,
            'feature_video': self.feature_video,
            'scrape_timestamp': self.scrape_timestamp,
            'social_links': self.social_links
        }

@dataclass
class Hashtag:
    """Hashtag data model with ranking and usage statistics.
    
    Represents a BitChute hashtag with trend ranking and associated
    video count information.
    
    Attributes:
        name: Hashtag name (with or without # prefix)
        url: Full URL to hashtag page
        rank: Trending rank position
        video_count: Number of videos using this hashtag
        scrape_timestamp: Unix timestamp when data was collected
    
    Example:
        >>> hashtag = Hashtag()
        >>> hashtag.name = "bitcoin"
        >>> hashtag.rank = 5
        >>> hashtag.video_count = 142
        >>> print(hashtag.formatted_name)  # "#bitcoin"
        >>> print(hashtag.clean_name)      # "bitcoin"
    """
    name: str = ""
    url: str = ""
    rank: int = 0
    video_count: Optional[int] = None
    scrape_timestamp: float = 0.0
    
    def __post_init__(self):
        """Initialize computed fields and set default values.
        
        Sets scrape timestamp to current time if not provided and constructs
        hashtag URL from name if not already set.
        """
        if not self.scrape_timestamp:
            self.scrape_timestamp = datetime.now(timezone.utc).timestamp()
        
        if not self.url and self.name:
            clean_name = self.name.lstrip('#')
            self.url = f"https://www.bitchute.com/hashtag/{clean_name}/"
    
    @property
    def clean_name(self) -> str:
        """Get hashtag name without # prefix.
        
        Returns:
            str: Hashtag name with # prefix removed.
            
        Example:
            >>> hashtag = Hashtag()
            >>> hashtag.name = "#bitcoin"
            >>> print(hashtag.clean_name)  # "bitcoin"
        """
        return self.name.lstrip('#') if self.name else ""
    
    @property
    def formatted_name(self) -> str:
        """Get hashtag name with # prefix.
        
        Returns:
            str: Hashtag name with # prefix added if not present.
            
        Example:
            >>> hashtag = Hashtag()
            >>> hashtag.name = "bitcoin"
            >>> print(hashtag.formatted_name)  # "#bitcoin"
        """
        if not self.name:
            return ""
        return f"#{self.clean_name}" if not self.name.startswith('#') else self.name
    
    def to_dict(self) -> dict:
        """Convert hashtag object to dictionary with computed properties.
        
        Returns:
            dict: Dictionary containing all hashtag data and computed properties.
        """
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
class Profile:
    """Profile data model for channel owners.
    
    Represents a BitChute user profile associated with channels.
    
    Attributes:
        profile_id: Unique profile identifier
        profile_name: Profile display name
        profile_url: Full URL to profile page
        profile_thumbnail_url: Profile avatar/thumbnail URL
    
    Example:
        >>> profile = Profile()
        >>> profile.profile_id = "abc123"
        >>> profile.profile_name = "Content Creator"
        >>> print(profile.profile_url)
    """
    profile_id: str = ""
    profile_name: str = ""
    profile_url: str = ""
    profile_thumbnail_url: str = ""
    
    def __post_init__(self):
        """Initialize computed fields.
        
        Constructs profile URL from ID if not already set.
        """
        if not self.profile_url and self.profile_id:
            self.profile_url = f"https://www.bitchute.com/profile/{self.profile_id}/"

@dataclass
class SearchResult:
    """Search result container with metadata.
    
    Container for search operation results including videos and channels
    with search metadata and pagination information.
    
    Attributes:
        query: Original search query string
        total_results: Total number of results available
        results_per_page: Number of results per page
        current_page: Current page number
        videos: List of video results
        channels: List of channel results
        search_timestamp: Unix timestamp when search was performed
    
    Example:
        >>> result = SearchResult()
        >>> result.query = "bitcoin"
        >>> result.videos = [video1, video2]
        >>> print(f"Found {result.video_count} videos")
        >>> print(f"Has results: {result.has_results}")
    """
    query: str = ""
    total_results: int = 0
    results_per_page: int = 0
    current_page: int = 0
    videos: List[Video] = field(default_factory=list)
    channels: List[Channel] = field(default_factory=list)
    search_timestamp: float = 0.0
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if not self.search_timestamp:
            self.search_timestamp = datetime.now(timezone.utc).timestamp()
    
    @property
    def has_results(self) -> bool:
        """Check if search returned any results.
        
        Returns:
            bool: True if videos or channels were found.
        """
        return len(self.videos) > 0 or len(self.channels) > 0
    
    @property
    def video_count(self) -> int:
        """Number of videos in results.
        
        Returns:
            int: Count of video results.
        """
        return len(self.videos)
    
    @property
    def channel_count(self) -> int:
        """Number of channels in results.
        
        Returns:
            int: Count of channel results.
        """
        return len(self.channels)

@dataclass
class APIStats:
    """API usage statistics and performance metrics.
    
    Tracks API usage patterns, performance metrics, and session statistics
    for monitoring and optimization purposes.
    
    Attributes:
        requests_made: Total number of API requests made
        successful_requests: Number of successful requests
        failed_requests: Number of failed requests
        cache_hits: Number of cache hits
        total_videos_scraped: Total videos collected
        total_channels_scraped: Total channels collected
        total_hashtags_scraped: Total hashtags collected
        session_start_time: Unix timestamp when session started
        last_request_time: Unix timestamp of most recent request
    
    Example:
        >>> stats = APIStats()
        >>> stats.requests_made = 100
        >>> stats.successful_requests = 95
        >>> print(f"Success rate: {stats.success_rate:.1%}")
        >>> print(f"Session duration: {stats.session_duration:.0f} seconds")
    """
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
        """Initialize session start time if not provided."""
        if not self.session_start_time:
            self.session_start_time = datetime.now(timezone.utc).timestamp()
    
    @property
    def success_rate(self) -> float:
        """Calculate request success rate.
        
        Returns:
            float: Success rate as proportion of total requests.
        """
        if self.requests_made == 0:
            return 0.0
        return self.successful_requests / self.requests_made
    
    @property
    def error_rate(self) -> float:
        """Calculate request error rate.
        
        Returns:
            float: Error rate as proportion of total requests.
        """
        if self.requests_made == 0:
            return 0.0
        return self.failed_requests / self.requests_made
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate.
        
        Returns:
            float: Cache hit rate as proportion of total attempts.
        """
        total_attempts = self.requests_made + self.cache_hits
        if total_attempts == 0:
            return 0.0
        return self.cache_hits / total_attempts
    
    @property
    def session_duration(self) -> float:
        """Calculate session duration in seconds.
        
        Returns:
            float: Duration of current session in seconds.
        """
        current_time = self.last_request_time if self.last_request_time else datetime.now(timezone.utc).timestamp()
        return current_time - self.session_start_time
    
    def to_dict(self) -> dict:
        """Convert statistics to dictionary format.
        
        Returns:
            dict: Complete statistics including computed metrics.
        """
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

@dataclass
class DownloadResult:
    """Download operation result with file information and statistics.
    
    Represents the result of a media download operation including
    success status, file paths, and performance metrics.
    
    Attributes:
        video_id: Video identifier for downloaded content
        success: Whether download operation succeeded
        thumbnail_path: Local path to downloaded thumbnail
        video_path: Local path to downloaded video file
        error_message: Error description if download failed
        download_time: Time taken for download in seconds
        file_size_bytes: Total size of downloaded files in bytes
    
    Example:
        >>> result = DownloadResult()
        >>> result.video_id = "abc123"
        >>> result.success = True
        >>> result.thumbnail_path = "/downloads/thumb.jpg"
        >>> result.file_size_bytes = 1048576
        >>> print(f"Downloaded: {result.file_size_formatted}")
        >>> print(f"Has thumbnail: {result.has_thumbnail}")
    """
    video_id: str = ""
    success: bool = False
    thumbnail_path: Optional[str] = None
    video_path: Optional[str] = None
    error_message: Optional[str] = None
    download_time: float = 0.0
    file_size_bytes: int = 0
    
    @property
    def has_thumbnail(self) -> bool:
        """Check if thumbnail was downloaded.
        
        Returns:
            bool: True if thumbnail path is set.
        """
        return self.thumbnail_path is not None
    
    @property
    def has_video(self) -> bool:
        """Check if video was downloaded.
        
        Returns:
            bool: True if video path is set.
        """
        return self.video_path is not None
    
    @property
    def file_size_formatted(self) -> str:
        """Get human-readable file size.
        
        Returns:
            str: Formatted file size with appropriate units.
            
        Example:
            >>> result = DownloadResult()
            >>> result.file_size_bytes = 1048576
            >>> print(result.file_size_formatted)  # "1.0 MB"
        """
        if self.file_size_bytes == 0:
            return "0 B"
        
        size = self.file_size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def to_dict(self) -> dict:
        """Convert download result to dictionary format.
        
        Returns:
            dict: Complete download result including computed properties.
        """
        return {
            'video_id': self.video_id,
            'success': self.success,
            'thumbnail_path': self.thumbnail_path,
            'video_path': self.video_path,
            'error_message': self.error_message,
            'download_time': self.download_time,
            'file_size_bytes': self.file_size_bytes,
            'file_size_formatted': self.file_size_formatted,
            'has_thumbnail': self.has_thumbnail,
            'has_video': self.has_video
        }
