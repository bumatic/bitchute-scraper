# PATCH 3: Add Download Parameters to Video Methods


    # After the detail fetching section, add:
    
    # Process downloads if requested
    if (download_thumbnails or download_videos) and all_videos:
        all_videos = self._process_downloads(
            all_videos, 
            download_thumbnails=download_thumbnails,
            download_videos=download_videos,
            force_redownload=force_redownload
        )
    
    # In the logging section, update to:
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
        
        logger.info(f"Retrieved {len(df)} trending videos ({timeframe}) {detail_status}{download_status}")




# PATCH 4: Add Return Type Consistency Methods

# Replace existing get_video_info method with this DataFrame-returning version


# Add new method for object access (backward compatibility)
def get_video_object(
    self, 
    video_id: str, 
    include_counts: bool = True, 
    include_media: bool = False
) -> Optional[Video]:
    """
    Get detailed video information as Video object
    
    This method provides object-based access for users who need the Video object interface.
    For consistency with other methods, prefer get_video_info() which returns a DataFrame.
    
    Args:
        video_id: Video ID to fetch details for
        include_counts: Include like/dislike/view counts  
        include_media: Include media URL
        
    Returns:
        Video object or None if not found
    """
    # Move existing get_video_info logic here
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

# Replace existing get_channel_info method with DataFrame-returning version
def get_channel_info(self, channel_id: str) -> pd.DataFrame:
    """
    Get detailed channel information as single-row DataFrame for consistency
    
    Args:
        channel_id: Channel ID to fetch details for
        
    Returns:
        Single-row DataFrame with channel information
        
    Note:
        This method now returns a DataFrame for consistency.
        Use get_channel_object() if you need a Channel object.
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

# Add new method for object access (backward compatibility)
def get_channel_object(self, channel_id: str) -> Optional[Channel]:
    """
    Get detailed channel information as Channel object
    
    This method provides object-based access for users who need the Channel object interface.
    For consistency with other methods, prefer get_channel_info() which returns a DataFrame.
    
    Args:
        channel_id: Channel ID to fetch details for
        
    Returns:
        Channel object or None if not found
    """
    # Move existing get_channel_info logic here
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