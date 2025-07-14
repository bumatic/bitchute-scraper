"""
BitChute API Scraper Test Suite
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import bitchute
test_dir = Path(__file__).parent
project_root = test_dir.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_DATA_DIR = test_dir / "fixtures"
