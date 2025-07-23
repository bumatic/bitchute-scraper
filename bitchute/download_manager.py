"""
BitChute Scraper Download Manager - Improved Version with Content-Based Deduplication

Enhanced download manager that prevents duplicate downloads of the same media content
by using URL-based hashing and content verification. Only downloads each unique
media file once, regardless of filename conflicts or multiple requests.

Key improvements:
- Content-based deduplication using URL hashing
- Database of downloaded media with metadata
- Smart filename generation without timestamps for identical content
- Conflict resolution only for genuinely different content
- Efficient lookup and reuse of existing downloads
"""

import re
import os
import time
import logging
import hashlib
import mimetypes
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse, parse_qs
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
    """Simple progress tracker when tqdm is not available."""
    
    def __init__(self, total: int = 0, desc: str = ""):
        self.total = total
        self.current = 0
        self.desc = desc

    def update(self, n: int = 1):
        self.current += n
        if self.total > 0:
            percent = (self.current / self.total) * 100
            print(
                f"\r{self.desc}: {self.current}/{self.total} ({percent:.1f}%)",
                end="",
                flush=True,
            )

    def close(self):
        print()


class MediaDownloadManager:
    """Enhanced download manager with content-based deduplication.
    
    Prevents duplicate downloads by tracking media URLs and reusing existing
    files when the same content is requested multiple times. Uses URL-based
    hashing to identify unique content and maintains a database of downloads.
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
        """Initialize enhanced download manager with deduplication."""
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

        # Download database for deduplication
        self.download_db_file = self.base_dir / "download_database.json"
        self.download_db = self._load_download_database()

        # Download statistics
        self.stats = {
            "total_downloads": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "skipped_downloads": 0,
            "reused_downloads": 0,  # New stat for reused files
            "total_bytes": 0,
        }

    def _create_directories(self):
        """Create necessary directory structure for downloads."""
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            (self.base_dir / self.thumbnail_folder).mkdir(exist_ok=True)
            (self.base_dir / self.video_folder).mkdir(exist_ok=True)

            if self.verbose:
                logger.info(f"Created download directories in {self.base_dir}")

        except Exception as e:
            raise ConfigurationError(f"Failed to create download directories: {e}")

    def _create_session(self) -> requests.Session:
        """Create optimized requests session for downloads."""
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

    def _load_download_database(self) -> Dict[str, Dict[str, Any]]:
        """Load download database from disk for deduplication tracking.
        
        Returns:
            Dict mapping URL hashes to download metadata including file paths.
        """
        if not self.download_db_file.exists():
            return {}

        try:
            with open(self.download_db_file, 'r', encoding='utf-8') as f:
                db = json.load(f)
                
            # Validate that files still exist and clean up orphaned entries
            valid_db = {}
            for url_hash, metadata in db.items():
                file_path = Path(metadata.get('file_path', ''))
                if file_path.exists() and file_path.stat().st_size > 0:
                    valid_db[url_hash] = metadata
                elif self.verbose:
                    logger.info(f"Cleaning orphaned database entry: {file_path}")
                    
            # Save cleaned database if changes were made
            if len(valid_db) != len(db):
                self._save_download_database(valid_db)
                
            return valid_db
            
        except Exception as e:
            if self.verbose:
                logger.warning(f"Failed to load download database: {e}")
            return {}

    def _save_download_database(self, db: Dict[str, Dict[str, Any]] = None):
        """Save download database to disk for persistence.
        
        Args:
            db: Optional database dict to save. Uses self.download_db if None.
        """
        try:
            db_to_save = db if db is not None else self.download_db
            with open(self.download_db_file, 'w', encoding='utf-8') as f:
                json.dump(db_to_save, f, indent=2, ensure_ascii=False)
                
            if self.verbose:
                logger.info(f"Saved download database with {len(db_to_save)} entries")
                
        except Exception as e:
            if self.verbose:
                logger.warning(f"Failed to save download database: {e}")

    def _get_content_hash(self, url: str) -> str:
        """Generate consistent hash for media URL to identify unique content.
        
        Creates a hash based on the URL while normalizing parameters that don't
        affect content (like timestamps, tokens, etc.) to ensure the same content
        gets the same hash regardless of URL variations.
        
        Args:
            url: Media URL to hash
            
        Returns:
            str: Consistent hash string for the content
        """
        try:
            parsed = urlparse(url)
            
            # Create base URL without query parameters that don't affect content
            base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # Parse query parameters and filter out ephemeral ones
            query_params = parse_qs(parsed.query) if parsed.query else {}
            
            # Remove parameters that are likely temporal/session-based
            ephemeral_params = {
                'timestamp', 'ts', 't', 'token', 'session', 'auth', 
                'sig', 'signature', 'expire', 'expires', '_'
            }
            
            filtered_params = {
                k: v for k, v in query_params.items() 
                if k.lower() not in ephemeral_params
            }
            
            # Sort parameters for consistency
            if filtered_params:
                sorted_params = sorted(filtered_params.items())
                param_string = '&'.join(f"{k}={','.join(sorted(v))}" for k, v in sorted_params)
                content_url = f"{base_url}?{param_string}"
            else:
                content_url = base_url
                
            # Generate hash
            return hashlib.md5(content_url.encode('utf-8')).hexdigest()
            
        except Exception as e:
            if self.verbose:
                logger.warning(f"Failed to hash URL {url}: {e}")
            # Fallback to simple hash of full URL
            return hashlib.md5(url.encode('utf-8')).hexdigest()

    def _get_base_filename(self, media_url: str, video_id: str, media_type: str, title: str = "") -> str:
        """Generate base filename without timestamp for consistent naming.
        
        Creates a standardized filename that will be the same for identical content,
        allowing for proper deduplication while still being descriptive.
        
        Args:
            media_url: URL of the media to download
            video_id: Video ID for filename generation
            media_type: Type of media ('thumbnail' or 'video')
            title: Optional video title for filename enhancement
            
        Returns:
            str: Base filename without extension
        """
        # Sanitize title for filename
        sanitized_title = self._sanitize_filename(title) if title else ""
        
        # Create base filename without timestamp
        if sanitized_title:
            base_filename = f"{video_id}_{sanitized_title}"
        else:
            base_filename = video_id
            
        # Limit length to prevent filesystem issues
        if len(base_filename) > 100:
            base_filename = base_filename[:100]
            
        return base_filename

    def _get_file_extension(self, media_url: str, media_type: str) -> str:
        """Determine appropriate file extension from URL or media type.
        
        Args:
            media_url: URL of the media to download
            media_type: Type of media ('thumbnail' or 'video')
            
        Returns:
            str: File extension including the dot
        """
        # Try to get extension from URL
        parsed_url = urlparse(media_url)
        url_path = parsed_url.path
        extension = Path(url_path).suffix.lower()
        
        # Default extensions if not found in URL
        if not extension:
            if media_type == "thumbnail":
                extension = ".jpg"
            else:
                extension = ".mp4"
                
        return extension

    def get_file_path(
        self, media_url: str, video_id: str, media_type: str, title: str = ""
    ) -> Path:
        """Get file path for media, reusing existing file if same content exists.
        
        This is the key method for deduplication. It checks if the same content
        has been downloaded before and returns the existing path if found.
        
        Args:
            media_url: URL of the media to download
            video_id: Video ID for filename generation
            media_type: Type of media ('thumbnail' or 'video')
            title: Optional video title for filename enhancement
            
        Returns:
            Path: File path to use (existing file or new path)
        """
        # Generate content hash for deduplication
        content_hash = self._get_content_hash(media_url)
        
        # Check if we already have this content
        if content_hash in self.download_db and not self.force_redownload:
            existing_metadata = self.download_db[content_hash]
            existing_path = Path(existing_metadata['file_path'])
            
            # Verify the file still exists and is valid
            if existing_path.exists() and existing_path.stat().st_size > 0:
                if self.verbose:
                    logger.info(f"Reusing existing file: {existing_path.name}")
                return existing_path
            else:
                # File was deleted or corrupted, remove from database
                if self.verbose:
                    logger.info(f"Existing file missing, will re-download: {existing_path}")
                del self.download_db[content_hash]
        
        # Generate new file path
        base_filename = self._get_base_filename(media_url, video_id, media_type, title)
        extension = self._get_file_extension(media_url, media_type)
        filename = f"{base_filename}{extension}"
        
        # Choose appropriate subfolder
        subfolder = (
            self.thumbnail_folder if media_type == "thumbnail" else self.video_folder
        )
        
        # Generate full path
        file_path = self.base_dir / subfolder / filename
        
        # Handle filename conflicts only for different content
        if file_path.exists():
            file_path = self._resolve_filename_conflict(file_path)
            
        return file_path

    def _sanitize_filename(self, filename: str, max_length: int = 50) -> str:
        """Sanitize filename for cross-platform compatibility."""
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
        
        This method is now only used for genuinely different content that
        happens to have the same filename, not for duplicate content.
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
        """Check if file exists and validate basic integrity."""
        if not file_path.exists():
            return False

        # Check if file is not empty
        if file_path.stat().st_size == 0:
            if self.verbose:
                logger.warning(f"Found empty file: {file_path}")
            return False

        return True

    def download_media(
        self,
        url: str,
        file_path: Path,
        show_progress: bool = True,
        expected_size: Optional[int] = None,
    ) -> bool:
        """Download media file with progress tracking and database updates.
        
        Enhanced version that also updates the download database for deduplication.
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

            # Update download database for deduplication
            content_hash = self._get_content_hash(url)
            with self._lock:
                self.download_db[content_hash] = {
                    'url': url,
                    'file_path': str(file_path),
                    'file_size': downloaded_bytes,
                    'download_time': time.time(),
                    'content_type': response.headers.get('content-type', '')
                }
                # Save database periodically (every 10 downloads)
                if len(self.download_db) % 10 == 0:
                    self._save_download_database()

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
        """Download multiple files concurrently with deduplication.
        
        Enhanced version that handles deduplication and reuse tracking.
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
            desc = f"Processing {len(valid_tasks)} files"
            if TQDM_AVAILABLE:
                batch_progress = tqdm(total=len(valid_tasks), desc=desc, unit="files")
            else:
                batch_progress = DownloadProgress(total=len(valid_tasks), desc=desc)

        def process_download_task(task: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
            """Process single download task with deduplication check.
            
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
                # Generate file path (includes deduplication check)
                file_path = self.get_file_path(url, video_id, media_type, title)
                
                # Check if this is a reused file
                content_hash = self._get_content_hash(url)
                is_reused = (content_hash in self.download_db and 
                           self.file_exists(file_path) and 
                           not self.force_redownload)
                
                if is_reused:
                    # File is being reused, update stats
                    with self._lock:
                        self.stats["reused_downloads"] += 1
                    
                    if self.verbose:
                        logger.info(f"Reusing existing file for {video_id}: {file_path.name}")
                else:
                    # Download file (without individual progress for batch downloads)
                    success = self.download_media(url, file_path, show_progress=False)
                    if not success:
                        file_path = None

                if batch_progress:
                    batch_progress.update(1)

                return video_id, media_type, str(file_path) if file_path else None

            except Exception as e:
                if self.verbose:
                    logger.error(f"Task failed for {video_id}: {e}")

                if batch_progress:
                    batch_progress.update(1)

                return video_id, media_type, None

        # Execute downloads concurrently
        with ThreadPoolExecutor(max_workers=self.max_concurrent_downloads) as executor:
            future_to_task = {
                executor.submit(process_download_task, task): task for task in valid_tasks
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

        # Save database after batch operation
        self._save_download_database()

        if self.verbose:
            successful_count = sum(
                1
                for video_results in results.values()
                for path in video_results.values()
                if path is not None
            )
            reused_count = self.stats["reused_downloads"]
            logger.info(
                f"Batch completed: {successful_count}/{len(download_tasks)} successful "
                f"({reused_count} reused existing files)"
            )

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive download statistics including deduplication metrics."""
        with self._lock:
            stats = self.stats.copy()

        # Add calculated statistics
        if stats["total_downloads"] > 0:
            stats["success_rate"] = (
                stats["successful_downloads"] / stats["total_downloads"]
            )
            stats["failure_rate"] = stats["failed_downloads"] / stats["total_downloads"]
            stats["skip_rate"] = stats["skipped_downloads"] / stats["total_downloads"]
            stats["reuse_rate"] = stats["reused_downloads"] / stats["total_downloads"]
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0
            stats["skip_rate"] = 0.0
            stats["reuse_rate"] = 0.0

        # Add deduplication stats
        stats["unique_content_items"] = len(self.download_db)
        
        # Format bytes
        stats["total_bytes_formatted"] = self._format_bytes(stats["total_bytes"])

        return stats

    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_count < 1024:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024
        return f"{bytes_count:.1f} TB"

    def reset_stats(self):
        """Reset all download statistics to zero."""
        with self._lock:
            self.stats = {
                "total_downloads": 0,
                "successful_downloads": 0,
                "failed_downloads": 0,
                "skipped_downloads": 0,
                "reused_downloads": 0,
                "total_bytes": 0,
            }

    def cleanup_database(self, verify_files: bool = True):
        """Clean up download database by removing entries for missing files.
        
        Args:
            verify_files: Whether to verify files still exist on disk
        """
        if not verify_files:
            return
            
        cleaned_count = 0
        with self._lock:
            entries_to_remove = []
            
            for content_hash, metadata in self.download_db.items():
                file_path = Path(metadata.get('file_path', ''))
                if not file_path.exists() or file_path.stat().st_size == 0:
                    entries_to_remove.append(content_hash)
                    cleaned_count += 1
                    
            for content_hash in entries_to_remove:
                del self.download_db[content_hash]
                
        if cleaned_count > 0:
            self._save_download_database()
            if self.verbose:
                logger.info(f"Cleaned {cleaned_count} orphaned entries from database")

    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the download database.
        
        Returns:
            Dict with database statistics and information
        """
        with self._lock:
            db_size = len(self.download_db)
            
        total_size = 0
        file_count = 0
        
        for metadata in self.download_db.values():
            total_size += metadata.get('file_size', 0)
            file_count += 1
            
        return {
            'database_file': str(self.download_db_file),
            'total_entries': db_size,
            'total_files': file_count,
            'total_size_bytes': total_size,
            'total_size_formatted': self._format_bytes(total_size),
            'database_exists': self.download_db_file.exists()
        }

    def cleanup(self):
        """Clean up resources and save database."""
        # Save database one final time
        self._save_download_database()
        
        if hasattr(self, "session"):
            self.session.close()

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point with cleanup."""
        self.cleanup()

    def __del__(self):
        """Cleanup on object destruction."""
        try:
            self.cleanup()
        except:
            pass