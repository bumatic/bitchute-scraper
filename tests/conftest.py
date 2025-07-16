"""
Pytest configuration and global fixtures
"""

import pytest
import sys
import os
from pathlib import Path
import logging
from unittest.mock import patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


def pytest_configure(config):
    """Configure pytest"""
    # Register custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests that require API access"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "selenium: marks tests that require Selenium/Chrome"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Add markers based on test location
    for item in items:
        # Add unit marker to all tests by default
        if "integration" not in item.keywords and "performance" not in item.keywords:
            item.add_marker(pytest.mark.unit)
        
        # Add selenium marker to token manager tests
        if "token_manager" in str(item.fspath):
            item.add_marker(pytest.mark.selenium)


@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory"""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment"""
    # Disable token caching during tests
    os.environ['BITCHUTE_DISABLE_TOKEN_CACHE'] = '1'
    
    # Set test mode
    os.environ['BITCHUTE_TEST_MODE'] = '1'
    
    yield
    
    # Cleanup
    os.environ.pop('BITCHUTE_DISABLE_TOKEN_CACHE', None)
    os.environ.pop('BITCHUTE_TEST_MODE', None)


@pytest.fixture(autouse=True)
def mock_token_manager():
    """Automatically mock token manager for all tests"""
    with patch('bitchute.core.TokenManager') as mock_tm:
        instance = mock_tm.return_value
        instance.get_token.return_value = "test_token_123456789012345678"
        instance.has_valid_token.return_value = True
        yield instance


@pytest.fixture
def no_rate_limit():
    """Disable rate limiting for tests"""
    with patch('bitchute.utils.RateLimiter.wait'):
        yield


@pytest.fixture
def fast_timeout():
    """Use fast timeout for tests"""
    with patch('bitchute.core.BitChuteAPI.__init__') as mock_init:
        def init(self, *args, **kwargs):
            kwargs['timeout'] = 1
            kwargs['rate_limit'] = 0
            original_init(self, *args, **kwargs)
        
        original_init = mock_init
        mock_init.side_effect = init
        yield


@pytest.fixture(scope="function")
def cleanup_files():
    """Cleanup files created during tests"""
    files_to_cleanup = []
    
    def add_file(filepath):
        files_to_cleanup.append(filepath)
    
    yield add_file
    
    # Cleanup
    for filepath in files_to_cleanup:
        path = Path(filepath)
        if path.exists():
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)


@pytest.fixture
def capture_logs():
    """Capture log output during tests"""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    logger = logging.getLogger('bitchute')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    logger.removeHandler(handler)


# Performance testing fixtures
@pytest.fixture
def benchmark_timer():
    """Simple benchmark timer"""
    import time
    
    class BenchmarkTimer:
        def __init__(self):
            self.times = {}
        
        def start(self, name):
            self.times[name] = {'start': time.time()}
        
        def stop(self, name):
            if name in self.times:
                self.times[name]['end'] = time.time()
                self.times[name]['duration'] = self.times[name]['end'] - self.times[name]['start']
        
        def get_duration(self, name):
            return self.times.get(name, {}).get('duration', 0)
        
        def report(self):
            for name, data in self.times.items():
                if 'duration' in data:
                    print(f"{name}: {data['duration']:.3f}s")
    
    return BenchmarkTimer()


# Skip markers for CI/CD
@pytest.fixture
def skip_in_ci():
    """Skip test if running in CI environment"""
    if os.environ.get('CI'):
        pytest.skip("Skipping in CI environment")


@pytest.fixture
def skip_without_chrome():
    """Skip test if Chrome is not available"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        driver.quit()
    except Exception:
        pytest.skip("Chrome/ChromeDriver not available")


# Mock external services
@pytest.fixture
def mock_external_services():
    """Mock all external service calls"""
    with patch('requests.Session.post') as mock_post, \
         patch('requests.Session.get') as mock_get, \
         patch('selenium.webdriver.Chrome') as mock_chrome:
        
        # Configure default responses
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"success": True}
        
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"success": True}
        
        yield {
            'post': mock_post,
            'get': mock_get,
            'chrome': mock_chrome
        }