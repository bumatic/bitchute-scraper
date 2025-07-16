# BitChute Scraper Testing Guide

## Overview

The BitChute scraper has a comprehensive test suite covering unit tests, integration tests, and performance benchmarks. The test suite is designed to ensure reliability, catch regressions, and validate the API behavior.

## Test Structure

```
tests/
├── __init__.py           # Test package initialization
├── conftest.py           # Pytest configuration and global fixtures
├── fixtures.py           # Shared test fixtures
├── helpers.py            # Test helper functions
├── test_core.py          # Core API tests
├── test_models.py        # Data model tests
├── test_validators.py    # Input validation tests
├── test_utils.py         # Utility function tests
├── test_token_manager.py # Token management tests
├── test_exceptions.py    # Exception handling tests
├── test_integration.py   # Integration tests
└── test_performance.py   # Performance benchmarks
```

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bitchute

# Run specific test file
pytest tests/test_core.py

# Run specific test
pytest tests/test_core.py::TestBitChuteAPI::test_api_initialization
```

### Using the Test Runner

```bash
# Run quick tests (default)
python run_tests.py

# Run all tests with coverage
python run_tests.py --type all --coverage

# Run only unit tests
python run_tests.py --type unit

# Run integration tests
python run_tests.py --type integration

# Run with verbose output
python run_tests.py -v

# Stop on first failure
python run_tests.py -x
```

### Using Make

```bash
# Run unit tests
make test

# Run all tests
make test-all

# Run with coverage
make coverage

# Run linting
make lint

# Run all checks
make check
```

### Using Tox

```bash
# Test all Python versions
tox

# Test specific Python version
tox -e py39

# Run linting only
tox -e flake8

# Run type checking
tox -e mypy
```

## Test Categories

### Unit Tests (Default)

Fast, isolated tests that mock external dependencies:

```bash
pytest -m unit
```

Examples:
- Model initialization and methods
- Validator functions
- Utility functions
- API client methods with mocked responses

### Integration Tests

Tests that verify component interactions:

```bash
pytest -m integration
```

Examples:
- End-to-end workflows
- Data pipeline processing
- Multi-component interactions
- Error recovery scenarios

### Performance Tests

Tests that measure and validate performance:

```bash
pytest -m performance
```

Examples:
- Large dataset handling
- Concurrent operations
- Rate limiting verification
- Memory usage tests

### Slow Tests

Tests that take longer to run:

```bash
# Run including slow tests
pytest

# Exclude slow tests
pytest -m "not slow"
```

## Test Fixtures

### Common Fixtures

```python
# Mock video data
@pytest.fixture
def mock_video_data():
    return {
        "video_id": "test123",
        "video_name": "Test Video",
        "view_count": 1000,
        # ...
    }

# Mock API client
@pytest.fixture
def mock_api_client():
    client = Mock(spec=BitChuteAPI)
    # Configure mock...
    return client

# Sample DataFrame
@pytest.fixture
def sample_dataframe():
    return pd.DataFrame({
        'id': ['v1', 'v2', 'v3'],
        'title': ['Video 1', 'Video 2', 'Video 3'],
        # ...
    })
```

### Auto-use Fixtures

Some fixtures are automatically applied:

- `mock_token_manager`: Automatically mocks token management
- `setup_test_environment`: Sets up test environment variables
- `reset_singleton_state`: Resets any singleton state between tests

## Writing Tests

### Test Structure

```python
class TestFeatureName:
    """Test feature description"""
    
    @pytest.fixture
    def setup_data(self):
        """Setup test data"""
        return {...}
    
    def test_normal_case(self, setup_data):
        """Test normal operation"""
        # Arrange
        data = setup_data
        
        # Act
        result = function_under_test(data)
        
        # Assert
        assert result == expected_value
    
    def test_edge_case(self):
        """Test edge cases"""
        with pytest.raises(ExpectedException):
            function_under_test(invalid_input)
    
    @pytest.mark.slow
    def test_performance(self):
        """Test performance requirements"""
        # Test implementation
```

### Testing Best Practices

1. **Use descriptive test names**
   ```python
   def test_get_trending_videos_with_invalid_timeframe_raises_validation_error():
       # Good: describes what, when, and expected outcome
   ```

2. **One assertion per test (when possible)**
   ```python
   def test_video_engagement_rate_calculation():
       video = Video(view_count=1000, like_count=80, dislike_count=20)
       assert video.engagement_rate == 0.1
   ```

3. **Use fixtures for common setup**
   ```python
   @pytest.fixture
   def api_with_mock_response(mock_response):
       api = BitChuteAPI()
       api._make_request = Mock(return_value=mock_response)
       return api
   ```

4. **Test error cases**
   ```python
   def test_api_handles_network_error():
       api = BitChuteAPI()
       api.session.post = Mock(side_effect=requests.ConnectionError)
       
       with pytest.raises(NetworkError):
           api.get_trending_videos()
   ```

5. **Use parametrize for similar tests**
   ```python
   @pytest.mark.parametrize("timeframe,expected", [
       ("day", "trending-day"),
       ("week", "trending-week"),
       ("month", "trending-month"),
   ])
   def test_timeframe_mapping(timeframe, expected):
       # Test implementation
   ```

## Coverage Requirements

- Minimum coverage: 80%
- Target coverage: 90%+
- Critical paths must have 100% coverage

Check coverage:

```bash
# Generate coverage report
pytest --cov=bitchute --cov-report=html

# View HTML report
open htmlcov/index.html
```

## Mocking Guidelines

### Mocking External Services

```python
# Mock requests
@patch('requests.Session.post')
def test_api_call(mock_post):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}
    mock_post.return_value = mock_response
    
    # Test code here
```

### Mocking Time-based Operations

```python
# Mock sleep for faster tests
@patch('time.sleep')
def test_rate_limiting(mock_sleep):
    # Test without actual delays
    pass

# Mock datetime for consistent results
@patch('datetime.datetime.now')
def test_timestamp(mock_now):
    mock_now.return_value = datetime(2024, 1, 1, 12, 0, 0)
    # Test code here
```

## Continuous Integration

Tests run automatically on:
- Every push to main/develop branches
- Every pull request
- Daily scheduled runs

CI Matrix:
- Python versions: 3.7, 3.8, 3.9, 3.10, 3.11, 3.12
- Operating systems: Ubuntu, Windows, macOS
- Additional checks: Linting, type checking, security scans

## Debugging Tests

### Run with debugging output

```bash
# Show print statements
pytest -s

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb

# Run specific test with full output
pytest -vvs tests/test_core.py::test_specific_function
```

### Common Issues

1. **Token Manager Mock Not Working**
   - Ensure `conftest.py` is in the tests directory
   - Check that the mock is being applied with `autouse=True`

2. **Import Errors**
   - Verify PYTHONPATH includes the project root
   - Check that `__init__.py` files exist

3. **Flaky Tests**
   - Use `pytest-timeout` for tests that might hang
   - Mock time-based operations
   - Use fixed random seeds

## Test Data

Test data is organized in:
- `tests/fixtures.py`: Mock data factories
- `tests/data/`: JSON test data files (if needed)

Example test data:

```python
# Create consistent test data
def create_mock_video_data(video_id="test123", **kwargs):
    base_data = {
        "video_id": video_id,
        "video_name": f"Test Video {video_id}",
        "view_count": 1000,
        # ...
    }
    base_data.update(kwargs)
    return base_data
```

## Performance Testing

Performance tests should:
- Set clear performance targets
- Use realistic data volumes
- Measure actual metrics

Example:

```python
@pytest.mark.performance
def test_large_dataset_processing():
    # Create 10,000 videos
    videos = [create_mock_video_data(f"v{i}") for i in range(10000)]
    
    start_time = time.time()
    processed = process_videos(videos)
    duration = time.time() - start_time
    
    assert len(processed) == 10000
    assert duration < 5.0  # Should process in under 5 seconds
```

## Contributing Tests

When contributing:

1. Write tests for new features
2. Ensure existing tests pass
3. Add integration tests for complex features
4. Update test documentation
5. Maintain or improve coverage

Test checklist:
- [ ] Unit tests for new functions/methods
- [ ] Error case coverage
- [ ] Integration test if applicable
- [ ] Performance test if applicable
- [ ] Documentation updated
- [ ] All tests passing locally
- [ ] Coverage maintained/improved