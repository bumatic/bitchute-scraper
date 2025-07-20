"""
BitChute Scraper Download Manager

Manages automatic downloading of thumbnails and videos with intelligent caching,
concurrent processing, and comprehensive error handling. Provides robust file
management capabilities including conflict resolution, progress tracking, and
download statistics.

This module implements a complete media download system with features including
smart filename generation, concurrent downloads, progress tracking, and
comprehensive statistics collection for performance monitoring.

Classes:
    DownloadProgress: Simple progress tracker when tqdm is not available
    MediaDownloadManager: Main download manager with caching and concurrency
"""

import re
import os
import time
import logging
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import NetworkError, ConfigurationError

logger = logging.getLogger(__name__)

try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


class DownloadProgress:
    """Simple progress tracker when tqdm is not available.

    Provides basic progress tracking functionality as a fallback when the
    tqdm library is not installed. Displays progress information to stdout
    with percentage completion updates.

    Attributes:
        total: Total number of items or bytes to process
        current: Current number of items or bytes processed
        desc: Description text to display with progress

    Example:
        >>> progress = DownloadProgress(total=100, desc="Downloading")
        >>> for i in range(100):
        ...     progress.update(1)
        >>> progress.close()
    """

    def __init__(self, total: int = 0, desc: str = ""):
        """Initialize progress tracker.

        Args:
            total: Total number of items or bytes expected
            desc: Description text for the progress display
        """
        self.total = total
        self.current = 0
        self.desc = desc

    def update(self, n: int = 1):
        """Update progress by specified amount.

        Args:
            n: Number of items or bytes to add to current progress

        Example:
            >>> progress = DownloadProgress(total=1000, desc="Processing")
            >>> progress.update(50)  # Add 50 to current progress
        """
        self.current += n
        if self.total > 0:
            percent = (self.current / self.total) * 100
            print(
                f"\r{self.desc}: {self.current}/{self.total} ({percent:.1f}%)",
                end="",
                flush=True,
            )

    def close(self):
        """Close progress tracker and print newline.

        Call this method when progress tracking is complete to ensure
        proper terminal formatting.
        """
        print()  # New line after progress


class MediaDownloadManager:
    """Manages automatic downloading of thumbnails and videos with smart caching.

    Provides comprehensive media download functionality including concurrent
    processing, intelligent filename generation, conflict resolution, and
    detailed progress tracking. Supports both thumbnail and video downloads
    with configurable directory structures and caching strategies.

    The manager handles automatic retry logic, file integrity checking,
    and provides detailed statistics for monitoring download performance.

    Attributes:
        base_dir: Base directory for all downloads
        thumbnail_folder: Subdirectory name for thumbnail files
        video_folder: Subdirectory name for video files
        force_redownload: Whether to redownload existing files
        max_concurrent_downloads: Maximum number of concurrent downloads
        timeout: Download timeout in seconds
        verbose: Whether to enable verbose logging

    Example:
        >>> manager = MediaDownloadManager(
        ...     base_dir="downloads",
        ...     max_concurrent_downloads=5,
        ...     verbose=True
        ... )
        >>>
        >>> # Download single file
        >>> success = manager.download_media(
        ...     "https://example.com/video.mp4",
        ...     Path("downloads/video.mp4")
        ... )
        >>>
        >>> # Download multiple files concurrently
        >>> tasks = [
        ...     {"url": "https://example.com/thumb1.jpg", "video_id": "vid1", "media_type": "thumbnail"},
        ...     {"url": "https://example.com/thumb2.jpg", "video_id": "vid2", "media_type": "thumbnail"}
        ... ]
        >>> results = manager.download_multiple(tasks)
    """

    def __init__(
        self,
        base_dir: str = "downloads",
        thumbnail_folder: str = "thumbnails",
        video_folder: str = "videos",
        force_redownload: bool = False,
        max_concurrent_downloads: int = 3,
        timeout: int = 30,
        verbose: bool = False,
    ):
        """Initialize download manager with configuration options.

        Args:
            base_dir: Base directory for all downloads
            thumbnail_folder: Subdirectory name for thumbnail files
            video_folder: Subdirectory name for video files
            force_redownload: Whether to redownload existing files
            max_concurrent_downloads: Maximum number of concurrent downloads
            timeout: Download timeout in seconds
            verbose: Whether to enable verbose logging

        Raises:
            ConfigurationError: If directory creation fails

        Example:
            >>> # Basic configuration
            >>> manager = MediaDownloadManager()
            >>>
            >>> # Advanced configuration
            >>> manager = MediaDownloadManager(
            ...     base_dir="/data/bitchute",
            ...     thumbnail_folder="thumbs",
            ...     video_folder="vids",
            ...     force_redownload=True,
            ...     max_concurrent_downloads=8,
            ...     timeout=60,
            ...     verbose=True
            ... )
        """
        self.base_dir = Path(base_dir)
        self.thumbnail_folder = thumbnail_folder
        self.video_folder = video_folder
        self.force_redownload = force_redownload
        self.max_concurrent_downloads = max_concurrent_downloads
        self.timeout = timeout
        self.verbose = verbose

        # Create directory structure
        self._create_directories()

        # Setup requests session with retries
        self.session = self._create_session()

        # Thread safety
        self._lock = threading.Lock()

        # Download statistics
        self.stats = {
            "total_downloads": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "skipped_downloads": 0,
            "total_bytes": 0,
        }

    def _create_directories(self):
        """Create necessary directory structure for downloads.

        Creates the base directory and subdirectories for thumbnails and
        videos if they don't already exist.

        Raises:
            ConfigurationError: If directory creation fails due to permissions
                or filesystem issues
        """
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            (self.base_dir / self.thumbnail_folder).mkdir(exist_ok=True)
            (self.base_dir / self.video_folder).mkdir(exist_ok=True)

            if self.verbose:
                logger.info(f"Created download directories in {self.base_dir}")

        except Exception as e:
            raise ConfigurationError(f"Failed to create download directories: {e}")

    def _create_session(self) -> requests.Session:
        """Create optimized requests session for downloads.

        Configures a requests session with retry logic, timeout settings,
        and appropriate headers for reliable media downloading.

        Returns:
            requests.Session: Configured session with retry strategy
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
            }
        )

        return session

    def get_file_path(
        self, media_url: str, video_id: str, media_type: str, title: str = ""
    ) -> Path:
        """Generate appropriate file path for media download.

        Creates a standardized file path based on the media type, video ID,
        and optional title. Handles file extension detection, filename
        sanitization, and conflict resolution.

        Args:
            media_url: URL of the media to download
            video_id: Video ID for filename generation
            media_type: Type of media ('thumbnail' or 'video')
            title: Optional video title for filename enhancement

        Returns:
            Path: Complete file path for the download

        Example:
            >>> manager = MediaDownloadManager()
            >>> path = manager.get_file_path(
            ...     "https://example.com/video.mp4",
            ...     "abc123",
            ...     "video",
            ...     "Sample Video Title"
            ... )
            >>> print(path)  # Path('downloads/videos/abc123_Sample_Video_Title_1640995200.mp4')
        """
        # Determine file extension from URL or content type
        parsed_url = urlparse(media_url)
        url_path = parsed_url.path

        # Try to get extension from URL
        extension = Path(url_path).suffix.lower()

        # Default extensions if not found in URL
        if not extension:
            if media_type == "thumbnail":
                extension = ".jpg"
            else:
                extension = ".mp4"

        # Sanitize title for filename
        sanitized_title = self._sanitize_filename(title) if title else ""

        # Generate timestamp for uniqueness
        timestamp = int(time.time())

        # Build filename
        if sanitized_title:
            filename = f"{video_id}_{sanitized_title}_{timestamp}{extension}"
        else:
            filename = f"{video_id}_{timestamp}{extension}"

        # Choose appropriate subfolder
        subfolder = (
            self.thumbnail_folder if media_type == "thumbnail" else self.video_folder
        )

        # Generate full path
        file_path = self.base_dir / subfolder / filename

        # Handle filename conflicts
        if file_path.exists() and not self.force_redownload:
            file_path = self._resolve_filename_conflict(file_path)

        return file_path

    def _sanitize_filename(self, filename: str, max_length: int = 50) -> str:
        """Sanitize filename for cross-platform compatibility.

        Removes or replaces characters that are invalid in filenames across
        different operating systems and ensures the filename is within
        reasonable length limits.

        Args:
            filename: Original filename to sanitize
            max_length: Maximum length for the sanitized filename

        Returns:
            str: Sanitized filename safe for all platforms

        Example:
            >>> manager = MediaDownloadManager()
            >>> safe_name = manager._sanitize_filename("Video: Title/Test*")
            >>> print(safe_name)  # "Video_Title_Test"
        """
        if not filename:
            return ""

        # Remove path traversal attempts
        filename = os.path.basename(filename)

        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")

        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

        # Remove extra whitespace and replace with underscores
        filename = "_".join(filename.split())

        # Truncate if too long
        if len(filename) > max_length:
            filename = filename[:max_length]

        # Remove trailing dots and spaces
        filename = filename.rstrip(". ")

        return filename[:255]

    def _resolve_filename_conflict(self, file_path: Path) -> Path:
        """Resolve filename conflicts by adding incrementing counter.

        When a file already exists at the target path, this method generates
        a new filename by appending an incrementing number until a unique
        filename is found.

        Args:
            file_path: Original file path that conflicts

        Returns:
            Path: New file path that doesn't conflict with existing files

        Example:
            >>> # If 'video.mp4' exists, returns 'video_1.mp4'
            >>> # If 'video_1.mp4' also exists, returns 'video_2.mp4'
            >>> manager = MediaDownloadManager()
            >>> unique_path = manager._resolve_filename_conflict(Path("video.mp4"))
        """
        base = file_path.stem
        suffix = file_path.suffix
        parent = file_path.parent

        counter = 1
        while file_path.exists():
            new_name = f"{base}_{counter}{suffix}"
            file_path = parent / new_name
            counter += 1

        return file_path

    def file_exists(self, file_path: Path) -> bool:
        """Check if file exists and validate basic integrity.

        Verifies that a file exists at the specified path and performs
        basic integrity checks such as ensuring the file is not empty.

        Args:
            file_path: Path to check for file existence and integrity

        Returns:
            bool: True if file exists and appears to be valid

        Example:
            >>> manager = MediaDownloadManager()
            >>> exists = manager.file_exists(Path("downloads/video.mp4"))
            >>> if exists:
            ...     print("File is present and valid")
        """
        if not file_path.exists():
            return False

        # Check if file is not empty
        if file_path.stat().st_size == 0:
            if self.verbose:
                logger.warning(f"Found empty file: {file_path}")
            return False

        # Additional integrity checks could be added here
        # (e.g., file header validation, checksum verification)

        return True

    def download_media(
        self,
        url: str,
        file_path: Path,
        show_progress: bool = True,
        expected_size: Optional[int] = None,
    ) -> bool:
        """Download media file with progress tracking and error handling.

        Downloads a media file from the specified URL to the local file path
        with optional progress tracking, retry logic, and comprehensive error
        handling. Supports streaming downloads for large files.

        Args:
            url: URL to download the media from
            file_path: Local file path to save the downloaded media
            show_progress: Whether to display download progress
            expected_size: Expected file size in bytes for progress tracking

        Returns:
            bool: True if download completed successfully, False otherwise

        Example:
            >>> manager = MediaDownloadManager()
            >>> success = manager.download_media(
            ...     "https://example.com/video.mp4",
            ...     Path("downloads/video.mp4"),
            ...     show_progress=True
            ... )
            >>> if success:
            ...     print("Download completed successfully")
        """
        if not url or not url.startswith(("http://", "https://")):
            if self.verbose:
                logger.warning(f"Invalid URL for download: {url}")
            return False

        try:
            # Check if file already exists and we're not forcing redownload
            if self.file_exists(file_path) and not self.force_redownload:
                if self.verbose:
                    logger.info(f"File already exists, skipping: {file_path.name}")
                with self._lock:
                    self.stats["skipped_downloads"] += 1
                return True

            # Create parent directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Start download
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()

            # Get content length for progress tracking
            content_length = response.headers.get("content-length")
            total_size = int(content_length) if content_length else expected_size

            # Setup progress tracking
            progress = None
            if show_progress and self.verbose:
                desc = f"Downloading {file_path.name}"
                if TQDM_AVAILABLE:
                    progress = tqdm(
                        total=total_size, unit="B", unit_scale=True, desc=desc
                    )
                else:
                    progress = DownloadProgress(total=total_size or 0, desc=desc)

            # Download file in chunks
            downloaded_bytes = 0
            chunk_size = 8192

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_bytes += len(chunk)

                        if progress:
                            progress.update(len(chunk))

            if progress:
                progress.close()

            # Update statistics
            with self._lock:
                self.stats["total_downloads"] += 1
                self.stats["successful_downloads"] += 1
                self.stats["total_bytes"] += downloaded_bytes

            if self.verbose:
                logger.info(
                    f"Downloaded: {file_path.name} ({downloaded_bytes:,} bytes)"
                )

            return True

        except requests.exceptions.RequestException as e:
            if self.verbose:
                logger.error(f"Download failed for {url}: {e}")

            # Clean up partial download
            if file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass

            with self._lock:
                self.stats["total_downloads"] += 1
                self.stats["failed_downloads"] += 1

            return False

        except Exception as e:
            if self.verbose:
                logger.error(f"Unexpected error downloading {url}: {e}")

            # Clean up partial download
            if file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass

            with self._lock:
                self.stats["total_downloads"] += 1
                self.stats["failed_downloads"] += 1

            return False

    def download_multiple(
        self, download_tasks: List[Dict[str, Any]], show_progress: bool = True
    ) -> Dict[str, Dict[str, Optional[str]]]:
        """Download multiple files concurrently with progress tracking.

        Processes multiple download tasks concurrently using a thread pool
        to improve overall download performance. Each task specifies the
        media URL, video ID, media type, and optional title.

        Args:
            download_tasks: List of download task dictionaries containing:
                - 'url': URL to download
                - 'video_id': Video ID for file naming
                - 'media_type': 'thumbnail' or 'video'
                - 'title': Video title (optional)
            show_progress: Whether to show overall progress tracking

        Returns:
            Dict[str, Dict[str, Optional[str]]]: Dictionary mapping video_id
                to dict of media_type -> local file path. Returns None for
                failed downloads.

        Example:
            >>> manager = MediaDownloadManager()
            >>> tasks = [
            ...     {
            ...         "url": "https://example.com/thumb1.jpg",
            ...         "video_id": "vid1",
            ...         "media_type": "thumbnail",
            ...         "title": "First Video"
            ...     },
            ...     {
            ...         "url": "https://example.com/thumb2.jpg",
            ...         "video_id": "vid2",
            ...         "media_type": "thumbnail",
            ...         "title": "Second Video"
            ...     }
            ... ]
            >>> results = manager.download_multiple(tasks)
            >>> print(results['vid1']['thumbnail'])  # Path to downloaded thumbnail
        """
        if not download_tasks:
            return {}

        results = {}

        # Filter out tasks with invalid URLs
        valid_tasks = [
            task
            for task in download_tasks
            if task.get("url") and task["url"].startswith(("http://", "https://"))
        ]

        if not valid_tasks:
            if self.verbose:
                logger.warning("No valid download tasks provided")
            return {task.get("video_id", ""): {} for task in download_tasks}

        if self.verbose:
            logger.info(
                f"Starting {len(valid_tasks)} downloads with {self.max_concurrent_downloads} workers"
            )

        # Setup progress tracking for batch
        batch_progress = None
        if show_progress and self.verbose:
            desc = f"Downloading {len(valid_tasks)} files"
            if TQDM_AVAILABLE:
                batch_progress = tqdm(total=len(valid_tasks), desc=desc, unit="files")
            else:
                batch_progress = DownloadProgress(total=len(valid_tasks), desc=desc)

        def download_task(task: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
            """Download single task and return result.

            Args:
                task: Dictionary containing download task information

            Returns:
                Tuple of (video_id, media_type, file_path or None)
            """
            video_id = task.get("video_id", "")
            media_type = task.get("media_type", "thumbnail")
            url = task["url"]
            title = task.get("title", "")

            try:
                # Generate file path
                file_path = self.get_file_path(url, video_id, media_type, title)

                # Download file (without individual progress for batch downloads)
                success = self.download_media(url, file_path, show_progress=False)

                if batch_progress:
                    batch_progress.update(1)

                return video_id, media_type, str(file_path) if success else None

            except Exception as e:
                if self.verbose:
                    logger.error(f"Task failed for {video_id}: {e}")

                if batch_progress:
                    batch_progress.update(1)

                return video_id, media_type, None

        # Execute downloads concurrently
        with ThreadPoolExecutor(max_workers=self.max_concurrent_downloads) as executor:
            future_to_task = {
                executor.submit(download_task, task): task for task in valid_tasks
            }

            for future in as_completed(future_to_task):
                video_id, media_type, file_path = future.result()
                if video_id not in results:
                    results[video_id] = {}
                results[video_id][media_type] = file_path

        if batch_progress:
            batch_progress.close()

        # Add None results for invalid tasks
        for task in download_tasks:
            video_id = task.get("video_id", "")
            media_type = task.get("media_type", "thumbnail")
            if video_id not in results:
                results[video_id] = {}
            if media_type not in results[video_id]:
                results[video_id][media_type] = None

        if self.verbose:
            successful_count = sum(
                1
                for video_results in results.values()
                for path in video_results.values()
                if path is not None
            )
            logger.info(
                f"Batch download completed: {successful_count}/{len(download_tasks)} successful"
            )

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive download statistics and performance metrics.

        Returns detailed statistics about download operations including
        success rates, total bytes downloaded, and calculated performance
        metrics.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - total_downloads: Total number of download attempts
                - successful_downloads: Number of successful downloads
                - failed_downloads: Number of failed downloads
                - skipped_downloads: Number of skipped (already existing) downloads
                - total_bytes: Total bytes downloaded
                - success_rate: Success rate as a decimal (0.0-1.0)
                - failure_rate: Failure rate as a decimal (0.0-1.0)
                - skip_rate: Skip rate as a decimal (0.0-1.0)
                - total_bytes_formatted: Human-readable formatted bytes

        Example:
            >>> manager = MediaDownloadManager()
            >>> # ... perform downloads ...
            >>> stats = manager.get_stats()
            >>> print(f"Success rate: {stats['success_rate']:.1%}")
            >>> print(f"Total downloaded: {stats['total_bytes_formatted']}")
        """
        with self._lock:
            stats = self.stats.copy()

        # Add calculated statistics
        if stats["total_downloads"] > 0:
            stats["success_rate"] = (
                stats["successful_downloads"] / stats["total_downloads"]
            )
            stats["failure_rate"] = stats["failed_downloads"] / stats["total_downloads"]
            stats["skip_rate"] = stats["skipped_downloads"] / stats["total_downloads"]
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0
            stats["skip_rate"] = 0.0

        # Format bytes
        stats["total_bytes_formatted"] = self._format_bytes(stats["total_bytes"])

        return stats

    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes in human-readable format.

        Converts byte counts to human-readable format with appropriate
        unit suffixes (B, KB, MB, GB, TB).

        Args:
            bytes_count: Number of bytes to format

        Returns:
            str: Formatted byte count with unit suffix

        Example:
            >>> manager = MediaDownloadManager()
            >>> formatted = manager._format_bytes(1048576)
            >>> print(formatted)  # "1.0 MB"
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_count < 1024:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024
        return f"{bytes_count:.1f} TB"

    def reset_stats(self):
        """Reset all download statistics to zero.

        Clears all accumulated download statistics including success counts,
        failure counts, and total bytes downloaded. Useful for starting
        fresh statistics collection after a batch operation.

        Example:
            >>> manager = MediaDownloadManager()
            >>> # ... perform downloads ...
            >>> manager.reset_stats()  # Clear all statistics
            >>> # ... perform new downloads with fresh statistics ...
        """
        with self._lock:
            self.stats = {
                "total_downloads": 0,
                "successful_downloads": 0,
                "failed_downloads": 0,
                "skipped_downloads": 0,
                "total_bytes": 0,
            }

    def cleanup(self):
        """Clean up resources and close connections.

        Properly closes the requests session and cleans up any resources
        used by the download manager. Should be called when the manager
        is no longer needed.

        Example:
            >>> manager = MediaDownloadManager()
            >>> try:
            ...     # Use manager for downloads
            ...     results = manager.download_multiple(tasks)
            ... finally:
            ...     manager.cleanup()
        """
        if hasattr(self, "session"):
            self.session.close()

    def __enter__(self):
        """Context manager entry point.

        Returns:
            MediaDownloadManager: Self for use in with statements
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point.

        Automatically cleans up resources when exiting the context manager.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        self.cleanup()

    def __del__(self):
        """Cleanup on object destruction.

        Ensures resources are cleaned up when the object is garbage collected.
        """
        try:
            self.cleanup()
        except:
            pass
