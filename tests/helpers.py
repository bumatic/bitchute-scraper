"""
Helper functions for BitChute scraper tests
"""

import pandas as pd
from typing import Any, Dict, List, Optional
import time
from contextlib import contextmanager
from pathlib import Path
import json


def assert_valid_dataframe(df: pd.DataFrame, expected_columns: List[str], min_rows: int = 0):
    """Assert that a DataFrame has expected structure"""
    assert isinstance(df, pd.DataFrame), "Result should be a DataFrame"
    
    for col in expected_columns:
        assert col in df.columns, f"Missing expected column: {col}"
    
    if min_rows > 0:
        assert len(df) >= min_rows, f"DataFrame has {len(df)} rows, expected at least {min_rows}"


def assert_valid_video(video: Any, check_details: bool = False):
    """Assert that a video object has valid data"""
    from bitchute.models import Video
    
    assert isinstance(video, Video), "Object should be a Video instance"
    assert video.id, "Video should have an ID"
    assert video.title, "Video should have a title"
    assert video.view_count >= 0, "View count should be non-negative"
    
    if check_details:
        assert video.like_count >= 0, "Like count should be non-negative"
        assert video.dislike_count >= 0, "Dislike count should be non-negative"


def assert_valid_channel(channel: Any):
    """Assert that a channel object has valid data"""
    from bitchute.models import Channel
    
    assert isinstance(channel, Channel), "Object should be a Channel instance"
    assert channel.id, "Channel should have an ID"
    assert channel.name, "Channel should have a name"
    assert channel.video_count >= 0, "Video count should be non-negative"


def assert_api_call_made(mock_obj, endpoint: str, expected_payload: Optional[Dict] = None):
    """Assert that an API call was made with expected parameters"""
    mock_obj.assert_called()
    
    # Check endpoint
    call_args = mock_obj.call_args
    assert endpoint in call_args[0][0], f"Expected endpoint {endpoint} not found in call"
    
    # Check payload if provided
    if expected_payload:
        actual_payload = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get('json', {})
        for key, value in expected_payload.items():
            assert key in actual_payload, f"Expected key {key} not in payload"
            assert actual_payload[key] == value, f"Expected {key}={value}, got {actual_payload[key]}"


@contextmanager
def time_limit(seconds: float):
    """Context manager to ensure code executes within time limit"""
    start_time = time.time()
    yield
    elapsed = time.time() - start_time
    assert elapsed < seconds, f"Execution took {elapsed:.2f}s, limit was {seconds}s"


def create_test_file(filepath: Path, content: str = "test content"):
    """Create a test file with given content"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content)
    return filepath


def load_test_data(filename: str) -> Dict:
    """Load test data from JSON file"""
    test_data_dir = Path(__file__).parent / "data"
    filepath = test_data_dir / filename
    
    if not filepath.exists():
        return {}
    
    with open(filepath, 'r') as f:
        return json.load(f)


def compare_dataframes(df1: pd.DataFrame, df2: pd.DataFrame, columns: Optional[List[str]] = None):
    """Compare two DataFrames for equality"""
    if columns:
        df1 = df1[columns]
        df2 = df2[columns]
    
    pd.testing.assert_frame_equal(df1, df2, check_dtype=False)


def mock_api_sequence(*responses):
    """Create a mock that returns different responses in sequence"""
    from unittest.mock import Mock
    
    mock = Mock()
    mock.side_effect = responses
    return mock


def assert_rate_limited(func, min_duration: float, calls: int = 2):
    """Assert that a function respects rate limiting"""
    start_time = time.time()
    
    for _ in range(calls):
        func()
    
    elapsed = time.time() - start_time
    assert elapsed >= min_duration, f"Rate limiting not enforced: {calls} calls took {elapsed:.2f}s"


def cleanup_test_files(*filepaths):
    """Clean up test files"""
    for filepath in filepaths:
        path = Path(filepath)
        if path.exists():
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)


def assert_valid_export_file(filepath: str, expected_format: str, min_size: int = 0):
    """Assert that an exported file is valid"""
    path = Path(filepath)
    
    assert path.exists(), f"Export file {filepath} does not exist"
    assert path.suffix == f".{expected_format}", f"Expected {expected_format} file, got {path.suffix}"
    
    if min_size > 0:
        size = path.stat().st_size
        assert size >= min_size, f"File size {size} bytes is less than minimum {min_size} bytes"
    
    # Format-specific validation
    if expected_format == 'csv':
        df = pd.read_csv(path)
        assert not df.empty, "CSV file is empty"
    elif expected_format == 'json':
        with open(path, 'r') as f:
            data = json.load(f)
            assert data, "JSON file is empty"
    elif expected_format == 'xlsx':
        df = pd.read_excel(path)
        assert not df.empty, "Excel file is empty"


def create_mock_chrome_options():
    """Create mock Chrome options for testing"""
    from unittest.mock import Mock
    
    options = Mock()
    options.add_argument = Mock()
    options.add_experimental_option = Mock()
    return options


def assert_valid_token(token: str):
    """Assert that a token has valid format"""
    assert isinstance(token, str), "Token should be a string"
    assert len(token) == 28, f"Token should be 28 characters, got {len(token)}"
    assert token.replace('_', '').replace('-', '').isalnum(), "Token should be alphanumeric with _ and -"


class MockResponse:
    """Mock response object for testing"""
    
    def __init__(self, json_data=None, status_code=200, text="", headers=None):
        self.json_data = json_data
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
    
    def json(self):
        if self.json_data is None:
            raise ValueError("No JSON data")
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code} Error")


def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
    """Wait for a condition to become true"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    
    return False