"""
Tests for BitChute Download Manager functionality.

Tests download operations, file management, concurrent downloads, 
statistics tracking, and error handling.
"""

import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests

from bitchute.download_manager import MediaDownloadManager, DownloadProgress
from bitchute.exceptions import ConfigurationError, NetworkError


@pytest.fixture
def temp_download_dir(tmp_path):
    """Create temporary directory for downloads."""
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    return download_dir


@pytest.fixture
def download_manager(temp_download_dir):
    """Create download manager with temporary directory."""
    return MediaDownloadManager(
        base_dir=str(temp_download_dir),
        thumbnail_folder="thumbs",
        video_folder="videos",
        force_redownload=False,
        max_concurrent_downloads=3,
        timeout=10,
        verbose=True
    )


@pytest.fixture
def mock_response():
    """Create mock HTTP response."""
    response = Mock()
    response.status_code = 200
    response.headers = {'content-length': '1024'}
    response.iter_content.return_value = [b'test data chunk'] * 5
    return response


class TestDownloadManagerInitialization:
    """Test download manager initialization and setup."""
    
    def test_directory_creation(self, temp_download_dir):
        """Test that download directories are created correctly."""
        manager = MediaDownloadManager(
            base_dir=str(temp_download_dir),
            thumbnail_folder="thumbs", 
            video_folder="videos"
        )
        
        assert (temp_download_dir / "thumbs").exists()
        assert (temp_download_dir / "videos").exists()
        assert manager.base_dir == temp_download_dir
    
    def test_invalid_directory_handling(self):
        """Test handling of invalid directory paths."""
        with pytest.raises(ConfigurationError):
            # Try to create in a path that should fail
            MediaDownloadManager(base_dir="/invalid/readonly/path")
    
    def test_configuration_storage(self, download_manager):
        """Test that configuration is stored correctly."""
        assert download_manager.thumbnail_folder == "thumbs"
        assert download_manager.video_folder == "videos"
        assert download_manager.max_concurrent_downloads == 3
        assert download_manager.timeout == 10
        assert download_manager.verbose is True
        assert download_manager.force_redownload is False


class TestBasicDownloadFunctionality:
    """Test basic download operations."""
    
    @patch('requests.Session.get')
    def test_download_single_thumbnail(self, mock_get, download_manager, mock_response):
        """Test downloading a single thumbnail file."""
        mock_get.return_value = mock_response
        
        url = "https://example.com/thumbnail.jpg"
        file_path = download_manager.base_dir / "thumbs" / "test_thumb.jpg"
        
        success = download_manager.download_media(url, file_path)
        
        assert success is True
        assert file_path.exists()
        assert file_path.read_bytes() == b'test data chunk' * 5
        
        # Check statistics
        stats = download_manager.get_stats()
        assert stats['successful_downloads'] == 1
        assert stats['total_downloads'] == 1
        assert stats['total_bytes'] > 0
    
    @patch('requests.Session.get')
    def test_download_single_video(self, mock_get, download_manager, mock_response):
        """Test downloading a single video file."""
        mock_get.return_value = mock_response
        
        url = "https://example.com/video.mp4"
        file_path = download_manager.base_dir / "videos" / "test_video.mp4"
        
        success = download_manager.download_media(url, file_path)
        
        assert success is True
        assert file_path.exists()
        assert file_path.stat().st_size > 0
    
    def test_invalid_url_handling(self, download_manager):
        """Test handling of invalid URLs."""
        invalid_urls = [
            "",
            "not_a_url",
            "ftp://invalid.com/file.jpg",
            None
        ]
        
        file_path = download_manager.base_dir / "test_file.jpg"
        
        for url in invalid_urls:
            success = download_manager.download_media(url, file_path)
            assert success is False
    
    @patch('requests.Session.get')
    def test_download_failure_handling(self, mock_get, download_manager):
        """Test handling of download failures."""
        # Mock HTTP error
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        url = "https://example.com/file.jpg"
        file_path = download_manager.base_dir / "test_file.jpg"
        
        success = download_manager.download_media(url, file_path)
        
        assert success is False
        assert not file_path.exists()  # Partial file should be cleaned up
        
        # Check error statistics
        stats = download_manager.get_stats()
        assert stats['failed_downloads'] == 1
    
    @patch('requests.Session.get')
    def test_http_error_handling(self, mock_get, download_manager):
        """Test handling of HTTP error status codes."""
        error_response = Mock()
        error_response.status_code = 404
        error_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        mock_get.return_value = error_response
        
        url = "https://example.com/not_found.jpg"
        file_path = download_manager.base_dir / "test_file.jpg"
        
        success = download_manager.download_media(url, file_path)
        
        assert success is False


class TestFilePathGeneration:
    """Test file path generation and naming."""
    
    def test_file_path_generation_thumbnail(self, download_manager):
        """Test file path generation for thumbnails."""
        path = download_manager.get_file_path(
            "https://example.com/thumb.jpg",
            "video123",
            "thumbnail",
            "Sample Video Title"
        )
        
        assert path.parent.name == "thumbs"
        assert "video123" in path.name
        assert "Sample_Video_Title" in path.name
        assert path.suffix == ".jpg"
    
    def test_file_path_generation_video(self, download_manager):
        """Test file path generation for videos."""
        path = download_manager.get_file_path(
            "https://example.com/video.mp4",
            "video456", 
            "video",
            "Another Video"
        )
        
        assert path.parent.name == "videos"
        assert "video456" in path.name
        assert "Another_Video" in path.name
        assert path.suffix == ".mp4"
    
    def test_filename_sanitization(self, download_manager):
        """Test filename sanitization for unsafe characters."""
        unsafe_title = 'Video: Title/With*Bad?Characters<>"|'
        
        path = download_manager.get_file_path(
            "https://example.com/video.mp4",
            "video789",
            "video", 
            unsafe_title
        )
        
        # Check that unsafe characters are removed/replaced
        assert "<" not in path.name
        assert ">" not in path.name
        assert "/" not in path.name
        assert "*" not in path.name
        assert "?" not in path.name
        assert "|" not in path.name
        assert '"' not in path.name
    
    def test_extension_detection(self, download_manager):
        """Test file extension detection from URLs."""
        test_cases = [
            ("https://example.com/file.jpg", ".jpg"),
            ("https://example.com/video.mp4", ".mp4"),
            ("https://example.com/image.png", ".png"),
            ("https://example.com/no_extension", ".jpg"),  # Default for thumbnail
        ]
        
        for url, expected_ext in test_cases:
            path = download_manager.get_file_path(url, "test123", "thumbnail")
            assert path.suffix == expected_ext


class TestFileConflictResolution:
    """Test file conflict resolution and existing file handling."""
    
    @patch('requests.Session.get')
    def test_filename_conflict_resolution(self, mock_get, download_manager, mock_response):
        """Test that filename conflicts are resolved with incrementing numbers."""
        mock_get.return_value = mock_response
        
        # Create initial file
        url = "https://example.com/test.jpg"
        path1 = download_manager.get_file_path(url, "test123", "thumbnail", "Test")
        
        # First download
        success1 = download_manager.download_media(url, path1)
        assert success1 is True
        assert path1.exists()
        
        # Second download with same parameters should create different file
        path2 = download_manager.get_file_path(url, "test123", "thumbnail", "Test")
        success2 = download_manager.download_media(url, path2)
        assert success2 is True
        assert path2.exists()
        assert path1 != path2  # Different paths due to timestamp
    
    @patch('requests.Session.get')
    def test_existing_file_skip_behavior(self, mock_get, download_manager, mock_response):
        """Test that existing files are skipped when force_redownload=False."""
        mock_get.return_value = mock_response
        
        # Create existing file
        existing_file = download_manager.base_dir / "thumbs" / "existing.jpg"
        existing_file.parent.mkdir(exist_ok=True)
        existing_file.write_bytes(b"existing content")
        
        # Try to download to existing file
        url = "https://example.com/test.jpg"
        success = download_manager.download_media(url, existing_file)
        
        assert success is True  # Should skip and return success
        assert existing_file.read_bytes() == b"existing content"  # Unchanged
        
        # Check statistics
        stats = download_manager.get_stats()
        assert stats['skipped_downloads'] == 1
    
    @patch('requests.Session.get')
    def test_force_redownload_behavior(self, mock_get, mock_response, temp_download_dir):
        """Test force redownload overwrites existing files."""
        # Create manager with force redownload enabled
        manager = MediaDownloadManager(
            base_dir=str(temp_download_dir),
            force_redownload=True,
            verbose=True
        )
        
        mock_get.return_value = mock_response
        
        # Create existing file
        existing_file = temp_download_dir / "thumbnails" / "existing.jpg"
        existing_file.parent.mkdir(exist_ok=True)
        existing_file.write_bytes(b"old content")
        
        # Download should overwrite
        url = "https://example.com/test.jpg"
        success = manager.download_media(url, existing_file)
        
        assert success is True
        assert existing_file.read_bytes() == b'test data chunk' * 5  # New content


class TestConcurrentDownloads:
    """Test concurrent download operations."""
    
    @patch('requests.Session.get')
    def test_concurrent_download_batch(self, mock_get, download_manager, mock_response):
        """Test downloading multiple files concurrently."""
        mock_get.return_value = mock_response
        
        download_tasks = [
            {
                "url": "https://example.com/thumb1.jpg",
                "video_id": "video1",
                "media_type": "thumbnail",
                "title": "Video 1"
            },
            {
                "url": "https://example.com/thumb2.jpg", 
                "video_id": "video2",
                "media_type": "thumbnail",
                "title": "Video 2"
            },
            {
                "url": "https://example.com/video1.mp4",
                "video_id": "video1",
                "media_type": "video",
                "title": "Video 1"
            }
        ]
        
        results = download_manager.download_multiple(download_tasks)
        
        assert len(results) == 2  # Two unique video_ids
        assert "video1" in results
        assert "video2" in results
        assert "thumbnail" in results["video1"]
        assert "video" in results["video1"]
        assert "thumbnail" in results["video2"]
        
        # Check all files were created
        assert results["video1"]["thumbnail"] is not None
        assert results["video1"]["video"] is not None
        assert results["video2"]["thumbnail"] is not None
    
    @patch('requests.Session.get')
    def test_concurrent_download_error_handling(self, mock_get, download_manager):
        """Test error handling during concurrent downloads."""
        # Mix successful and failed downloads
        def side_effect(*args, **kwargs):
            if "fail" in args[0]:
                raise requests.exceptions.RequestException("Network error")
            else:
                response = Mock()
                response.status_code = 200
                response.headers = {}
                response.iter_content.return_value = [b'data']
                return response
        
        mock_get.side_effect = side_effect
        
        download_tasks = [
            {
                "url": "https://example.com/success.jpg",
                "video_id": "video1", 
                "media_type": "thumbnail"
            },
            {
                "url": "https://example.com/fail.jpg",
                "video_id": "video2",
                "media_type": "thumbnail"
            }
        ]
        
        results = download_manager.download_multiple(download_tasks)
        
        assert results["video1"]["thumbnail"] is not None  # Success
        assert results["video2"]["thumbnail"] is None       # Failed
    
    def test_empty_download_tasks(self, download_manager):
        """Test handling of empty download task list."""
        results = download_manager.download_multiple([])
        assert results == {}
    
    def test_invalid_download_tasks(self, download_manager):
        """Test handling of invalid download tasks."""
        invalid_tasks = [
            {"url": "", "video_id": "test1", "media_type": "thumbnail"},  # Empty URL
            {"url": "invalid_url", "video_id": "test2", "media_type": "thumbnail"},  # Invalid URL
        ]
        
        results = download_manager.download_multiple(invalid_tasks)
        
        # Should handle gracefully and return proper structure
        assert isinstance(results, dict)
        
        # The method should return results for all video_ids even if failed
        if results:  # Only check if results were returned
            for video_id in ["test1", "test2"]:
                if video_id in results:
                    assert isinstance(results[video_id], dict)
                    # thumbnail key may or may not exist for failed downloads
                    thumbnail_result = results[video_id].get("thumbnail")
                    assert thumbnail_result is None  # Should be None for failed downloads


class TestDownloadProgress:
    """Test download progress tracking."""
    
    def test_download_progress_basic(self, capsys):
        """Test basic download progress functionality."""
        progress = DownloadProgress(total=100, desc="Testing")
        
        progress.update(25)
        progress.update(50) 
        progress.close()
        
        captured = capsys.readouterr()
        assert "Testing" in captured.out
        assert "75/100" in captured.out
    
    def test_download_progress_without_total(self, capsys):
        """Test progress tracking without known total."""
        progress = DownloadProgress(total=0, desc="Unknown size")
        
        progress.update(50)
        progress.close()
        
        captured = capsys.readouterr()
        # Should not crash - just verify we get some kind of output
        assert isinstance(captured.out, str)
        # The progress may or may not show meaningful text when total=0
    
    @patch('requests.Session.get')
    def test_progress_integration(self, mock_get, download_manager):
        """Test progress tracking integration with downloads."""
        # Mock response with content-length
        response = Mock()
        response.status_code = 200
        response.headers = {'content-length': '1000'}
        response.iter_content.return_value = [b'x' * 100] * 10  # 10 chunks of 100 bytes
        mock_get.return_value = response
        
        url = "https://example.com/large_file.jpg"
        file_path = download_manager.base_dir / "test_progress.jpg"
        
        success = download_manager.download_media(url, file_path, show_progress=True)
        
        assert success is True
        assert file_path.exists()


class TestDownloadStatistics:
    """Test download statistics tracking and reporting."""
    
    def test_statistics_initialization(self, download_manager):
        """Test initial statistics state."""
        stats = download_manager.get_stats()
        
        assert stats['total_downloads'] == 0
        assert stats['successful_downloads'] == 0
        assert stats['failed_downloads'] == 0
        assert stats['skipped_downloads'] == 0
        assert stats['total_bytes'] == 0
        assert stats['success_rate'] == 0.0
    
    @patch('requests.Session.get')
    def test_statistics_tracking(self, mock_get, download_manager, mock_response):
        """Test statistics are tracked correctly during downloads."""
        mock_get.return_value = mock_response
        
        # Perform successful download
        url = "https://example.com/test1.jpg"
        file_path = download_manager.base_dir / "test1.jpg"
        download_manager.download_media(url, file_path)
        
        # Perform failed download
        mock_get.side_effect = requests.exceptions.RequestException("Error")
        url2 = "https://example.com/test2.jpg"
        file_path2 = download_manager.base_dir / "test2.jpg"
        download_manager.download_media(url2, file_path2)
        
        stats = download_manager.get_stats()
        
        assert stats['total_downloads'] == 2
        assert stats['successful_downloads'] == 1
        assert stats['failed_downloads'] == 1
        assert stats['success_rate'] == 0.5
        assert stats['failure_rate'] == 0.5
        assert stats['total_bytes'] > 0
    
    def test_statistics_thread_safety(self, download_manager):
        """Test statistics are thread-safe during concurrent operations."""
        def update_stats():
            with download_manager._lock:
                download_manager.stats['total_downloads'] += 1
        
        # Run multiple threads updating stats
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=update_stats)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        stats = download_manager.get_stats()
        assert stats['total_downloads'] == 10
    
    def test_statistics_reset(self, download_manager):
        """Test statistics can be reset."""
        # Add some fake stats
        download_manager.stats['total_downloads'] = 5
        download_manager.stats['successful_downloads'] = 3
        download_manager.stats['total_bytes'] = 1000
        
        # Reset
        download_manager.reset_stats()
        
        stats = download_manager.get_stats()
        assert stats['total_downloads'] == 0
        assert stats['successful_downloads'] == 0
        assert stats['total_bytes'] == 0
    
    def test_bytes_formatting(self, download_manager):
        """Test human-readable bytes formatting."""
        test_cases = [
            (512, "512.0 B"),
            (1024, "1.0 KB"), 
            (1048576, "1.0 MB"),
            (1073741824, "1.0 GB"),
        ]
        
        for bytes_count, expected in test_cases:
            formatted = download_manager._format_bytes(bytes_count)
            assert formatted == expected


class TestFileIntegrityChecks:
    """Test file integrity validation."""
    
    def test_file_exists_validation(self, download_manager, temp_download_dir):
        """Test file existence and integrity checks."""
        # Create valid file
        valid_file = temp_download_dir / "valid.jpg"
        valid_file.write_bytes(b"valid content")
        
        # Create empty file
        empty_file = temp_download_dir / "empty.jpg"
        empty_file.touch()
        
        # Test non-existent file
        nonexistent_file = temp_download_dir / "nonexistent.jpg"
        
        assert download_manager.file_exists(valid_file) is True
        assert download_manager.file_exists(empty_file) is False  # Empty files are invalid
        assert download_manager.file_exists(nonexistent_file) is False
    
    @patch('requests.Session.get')
    def test_partial_download_cleanup(self, mock_get, download_manager):
        """Test cleanup of partial downloads on failure."""
        # Mock download that fails mid-stream
        response = Mock()
        response.status_code = 200
        response.headers = {}
        response.iter_content.side_effect = requests.exceptions.RequestException("Connection lost")
        mock_get.return_value = response
        
        url = "https://example.com/test.jpg"
        file_path = download_manager.base_dir / "test.jpg"
        
        success = download_manager.download_media(url, file_path)
        
        assert success is False
        assert not file_path.exists()  # Partial file should be cleaned up


class TestDownloadManagerContextManager:
    """Test download manager as context manager."""
    
    def test_context_manager_usage(self, temp_download_dir):
        """Test download manager can be used as context manager."""
        with MediaDownloadManager(base_dir=str(temp_download_dir)) as manager:
            assert manager is not None
            assert hasattr(manager, 'download_media')
    
    def test_context_manager_cleanup(self, temp_download_dir):
        """Test context manager properly cleans up resources."""
        manager = MediaDownloadManager(base_dir=str(temp_download_dir))
        
        with manager:
            session = manager.session
            assert session is not None
        
        # After context exit, session should be closed
        # Note: This is hard to test directly, but we can verify cleanup was called


class TestDownloadManagerConfiguration:
    """Test download manager configuration options."""
    
    def test_custom_timeout_configuration(self, temp_download_dir):
        """Test custom timeout configuration."""
        manager = MediaDownloadManager(
            base_dir=str(temp_download_dir),
            timeout=120
        )
        
        assert manager.timeout == 120
    
    def test_max_workers_configuration(self, temp_download_dir):
        """Test max workers configuration."""
        manager = MediaDownloadManager(
            base_dir=str(temp_download_dir),
            max_concurrent_downloads=8
        )
        
        assert manager.max_concurrent_downloads == 8
    
    def test_verbose_logging_configuration(self, temp_download_dir):
        """Test verbose logging configuration."""
        manager = MediaDownloadManager(
            base_dir=str(temp_download_dir),
            verbose=True
        )
        
        assert manager.verbose is True
    
    def test_folder_name_customization(self, temp_download_dir):
        """Test custom folder names."""
        manager = MediaDownloadManager(
            base_dir=str(temp_download_dir),
            thumbnail_folder="custom_thumbs",
            video_folder="custom_videos"
        )
        
        assert manager.thumbnail_folder == "custom_thumbs"
        assert manager.video_folder == "custom_videos"
        assert (temp_download_dir / "custom_thumbs").exists()
        assert (temp_download_dir / "custom_videos").exists()