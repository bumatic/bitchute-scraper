"""
BitChute Scraper Download Manager
Handles automatic downloading of thumbnails and videos with smart caching
"""

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
    """Simple progress tracker when tqdm is not available"""
    
    def __init__(self, total: int = 0, desc: str = ""):
        self.total = total
        self.current = 0
        self.desc = desc
        
    def update(self, n: int = 1):
        self.current += n
        if self.total > 0:
            percent = (self.current / self.total) * 100
            print(f"\r{self.desc}: {self.current}/{self.total} ({percent:.1f}%)", end="", flush=True)
    
    def close(self):
        print()  # New line after progress


class MediaDownloadManager:
    """
    Manages automatic downloading of thumbnails and videos with smart caching
    """
    
    def __init__(
        self, 
        base_dir: str = "downloads",
        thumbnail_folder: str = "thumbnails",
        video_folder: str = "videos",
        force_redownload: bool = False,
        max_concurrent_downloads: int = 3,
        timeout: int = 30,
        verbose: bool = False
    ):
        """
        Initialize download manager
        
        Args:
            base_dir: Base directory for all downloads
            thumbnail_folder: Subdirectory for thumbnail files
            video_folder: Subdirectory for video files
            force_redownload: Whether to redownload existing files
            max_concurrent_downloads: Maximum concurrent downloads
            timeout: Download timeout in seconds
            verbose: Enable verbose logging
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
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'skipped_downloads': 0,
            'total_bytes': 0
        }
    
    def _create_directories(self):
        """Create necessary directory structure"""
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            (self.base_dir / self.thumbnail_folder).mkdir(exist_ok=True)
            (self.base_dir / self.video_folder).mkdir(exist_ok=True)
            
            if self.verbose:
                logger.info(f"Created download directories in {self.base_dir}")
                
        except Exception as e:
            raise ConfigurationError(f"Failed to create download directories: {e}")
    
    def _create_session(self) -> requests.Session:
        """Create optimized requests session for downloads"""
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
        session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/91.0.4472.124 Safari/537.36'
            )
        })
        
        return session
    
    def get_file_path(
        self, 
        media_url: str, 
        video_id: str, 
        media_type: str,
        title: str = ""
    ) -> Path:
        """
        Generate file path for media download
        
        Args:
            media_url: URL of the media to download
            video_id: Video ID for file naming
            media_type: 'thumbnail' or 'video'
            title: Video title for filename (optional)
            
        Returns:
            Path object for the file
        """
        # Determine file extension from URL or content type
        parsed_url = urlparse(media_url)
        url_path = parsed_url.path
        
        # Try to get extension from URL
        extension = Path(url_path).suffix.lower()
        
        # Default extensions if not found in URL
        if not extension:
            if media_type == 'thumbnail':
                extension = '.jpg'
            else:
                extension = '.mp4'
        
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
        subfolder = self.thumbnail_folder if media_type == 'thumbnail' else self.video_folder
        
        # Generate full path
        file_path = self.base_dir / subfolder / filename
        
        # Handle filename conflicts
        if file_path.exists() and not self.force_redownload:
            file_path = self._resolve_filename_conflict(file_path)
        
        return file_path
    
    def _sanitize_filename(self, filename: str, max_length: int = 50) -> str:
        """
        Sanitize filename for cross-platform compatibility
        
        Args:
            filename: Original filename
            max_length: Maximum length for filename part
            
        Returns:
            Sanitized filename
        """
        if not filename:
            return ""
        
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove extra whitespace and replace with underscores
        filename = '_'.join(filename.split())
        
        # Truncate if too long
        if len(filename) > max_length:
            filename = filename[:max_length]
        
        # Remove trailing dots and spaces
        filename = filename.rstrip('. ')
        
        return filename
    
    def _resolve_filename_conflict(self, file_path: Path) -> Path:
        """
        Resolve filename conflicts by adding incrementing counter
        
        Args:
            file_path: Original file path
            
        Returns:
            New file path that doesn't conflict
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
        """
        Check if file exists and validate basic integrity
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file exists and appears valid
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
        expected_size: Optional[int] = None
    ) -> bool:
        """
        Download media file with progress tracking
        
        Args:
            url: URL to download
            file_path: Local file path to save to
            show_progress: Whether to show progress bar
            expected_size: Expected file size for progress tracking
            
        Returns:
            True if download successful, False otherwise
        """
        if not url or not url.startswith(('http://', 'https://')):
            if self.verbose:
                logger.warning(f"Invalid URL for download: {url}")
            return False
        
        try:
            # Check if file already exists and we're not forcing redownload
            if self.file_exists(file_path) and not self.force_redownload:
                if self.verbose:
                    logger.info(f"File already exists, skipping: {file_path.name}")
                with self._lock:
                    self.stats['skipped_downloads'] += 1
                return True
            
            # Create parent directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Start download
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            # Get content length for progress tracking
            content_length = response.headers.get('content-length')
            total_size = int(content_length) if content_length else expected_size
            
            # Setup progress tracking
            progress = None
            if show_progress and self.verbose:
                desc = f"Downloading {file_path.name}"
                if TQDM_AVAILABLE:
                    progress = tqdm(total=total_size, unit='B', unit_scale=True, desc=desc)
                else:
                    progress = DownloadProgress(total=total_size or 0, desc=desc)
            
            # Download file in chunks
            downloaded_bytes = 0
            chunk_size = 8192
            
            with open(file_path, 'wb') as f:
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
                self.stats['total_downloads'] += 1
                self.stats['successful_downloads'] += 1
                self.stats['total_bytes'] += downloaded_bytes
            
            if self.verbose:
                logger.info(f"Downloaded: {file_path.name} ({downloaded_bytes:,} bytes)")
            
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
                self.stats['total_downloads'] += 1
                self.stats['failed_downloads'] += 1
            
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
                self.stats['total_downloads'] += 1
                self.stats['failed_downloads'] += 1
            
            return False
    
    def download_multiple(
        self, 
        download_tasks: List[Dict[str, Any]], 
        show_progress: bool = True
    ) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Download multiple files concurrently
        
        Args:
            download_tasks: List of download task dictionaries containing:
                - 'url': URL to download
                - 'video_id': Video ID for file naming
                - 'media_type': 'thumbnail' or 'video'
                - 'title': Video title (optional)
            show_progress: Whether to show progress
            
        Returns:
            Dictionary mapping video_id to dict of media_type -> local file path
        """
        if not download_tasks:
            return {}
        
        results = {}
        
        # Filter out tasks with invalid URLs
        valid_tasks = [
            task for task in download_tasks 
            if task.get('url') and task['url'].startswith(('http://', 'https://'))
        ]
        
        if not valid_tasks:
            if self.verbose:
                logger.warning("No valid download tasks provided")
            return {task.get('video_id', ''): {} for task in download_tasks}
        
        if self.verbose:
            logger.info(f"Starting {len(valid_tasks)} downloads with {self.max_concurrent_downloads} workers")
        
        # Setup progress tracking for batch
        batch_progress = None
        if show_progress and self.verbose:
            desc = f"Downloading {len(valid_tasks)} files"
            if TQDM_AVAILABLE:
                batch_progress = tqdm(total=len(valid_tasks), desc=desc, unit="files")
            else:
                batch_progress = DownloadProgress(total=len(valid_tasks), desc=desc)
        
        def download_task(task: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
            """Download single task and return result"""
            video_id = task.get('video_id', '')
            media_type = task.get('media_type', 'thumbnail')
            url = task['url']
            title = task.get('title', '')
            
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
                executor.submit(download_task, task): task 
                for task in valid_tasks
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
            video_id = task.get('video_id', '')
            media_type = task.get('media_type', 'thumbnail')
            if video_id not in results:
                results[video_id] = {}
            if media_type not in results[video_id]:
                results[video_id][media_type] = None
        
        if self.verbose:
            successful_count = sum(
                1 for video_results in results.values() 
                for path in video_results.values() 
                if path is not None
            )
            logger.info(f"Batch download completed: {successful_count}/{len(download_tasks)} successful")
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get download statistics"""
        with self._lock:
            stats = self.stats.copy()
        
        # Add calculated statistics
        if stats['total_downloads'] > 0:
            stats['success_rate'] = stats['successful_downloads'] / stats['total_downloads']
            stats['failure_rate'] = stats['failed_downloads'] / stats['total_downloads']
            stats['skip_rate'] = stats['skipped_downloads'] / stats['total_downloads']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
            stats['skip_rate'] = 0.0
        
        # Format bytes
        stats['total_bytes_formatted'] = self._format_bytes(stats['total_bytes'])
        
        return stats
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024
        return f"{bytes_count:.1f} TB"
    
    def reset_stats(self):
        """Reset download statistics"""
        with self._lock:
            self.stats = {
                'total_downloads': 0,
                'successful_downloads': 0,
                'failed_downloads': 0,
                'skipped_downloads': 0,
                'total_bytes': 0
            }
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'session'):
            self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.cleanup()
        except:
            pass