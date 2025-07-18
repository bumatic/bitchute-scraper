BitChute Scraper Installation Guide
This guide covers installation, building, and packaging of the BitChute Scraper package.

Quick Installation
From PyPI (Recommended)
bash
# Basic installation
pip3 install bitchute-scraper

From Source
bash
# Clone the repository
git clone https://github.com/bumatic/bitchute-scraper.git
cd bitchute-scraper

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e .[dev]
Installation Options
Feature-specific Installations
bash
# Progress bars for downloads
pip install bitchute-scraper[progress]

# Fast data formats (Parquet)
pip install bitchute-scraper[fast]

# System monitoring
pip install bitchute-scraper[monitoring]

# YAML configuration support
pip install bitchute-scraper[config]

# Documentation tools
pip install bitchute-scraper[docs]

# Testing tools only
pip install bitchute-scraper[test]

# Code quality tools
pip install bitchute-scraper[lint]
Combined Installations
bash
# Multiple extras
pip install bitchute-scraper[progress,fast,monitoring]

# Everything
pip install bitchute-scraper[full,dev,docs]
Development Setup
1. Clone and Setup Environment
bash
# Clone repository
git clone https://github.com/bumatic/bitchute-scraper.git
cd bitchute-scraper

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
2. Install Development Dependencies
bash
# Install all development dependencies
pip install -r requirements-dev.txt

# Or install with extras
pip install -e .[dev,docs,test]
3. Setup Pre-commit Hooks (Optional)
bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run on all files (optional)
pre-commit run --all-files
Building the Package
1. Install Build Tools
bash
pip install build twine wheel
2. Build Distribution
bash
# Build source and wheel distributions
python -m build

# This creates:
# - dist/bitchute-scraper-1.1.0.tar.gz (source distribution)
# - dist/bitchute_scraper-1.1.0-py3-none-any.whl (wheel distribution)
3. Verify Build
bash
# Check the built packages
twine check dist/*

# Install locally to test
pip install dist/bitchute_scraper-1.1.0-py3-none-any.whl
Testing
Run Tests
bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bitchute --cov-report=html

# Run specific test categories
pytest -m "not slow"  # Skip slow tests
pytest -m unit        # Only unit tests
pytest -m integration # Only integration tests
Code Quality Checks
bash
# Format code
black bitchute/

# Check code style
flake8 bitchute/

# Type checking
mypy bitchute/

# Security scanning
bandit -r bitchute/

# All quality checks
black bitchute/ && flake8 bitchute/ && mypy bitchute/ && pytest
Requirements Management
Core Requirements Structure
requirements.txt - All dependencies with explanations
requirements-dev.txt - Development dependencies only
setup.py - Package configuration with install_requires
pyproject.toml - Modern Python packaging configuration
Updating Requirements
bash
# Install pip-tools for requirements management
pip install pip-tools

# Update requirements files
pip-compile requirements.in
pip-compile requirements-dev.in

# Sync environment with requirements
pip-sync requirements.txt requirements-dev.txt
Troubleshooting
Common Issues
1. ChromeDriver Issues
bash
# Ensure Chrome is installed
# webdriver-manager handles driver downloads automatically
# For headless servers, install chrome-headless:
sudo apt-get install chromium-browser  # Ubuntu/Debian
2. Pandas Installation Issues
bash
# On some systems, install numpy first
pip install numpy
pip install pandas

# For Apple Silicon Macs
conda install pandas  # or use brew
3. Permission Issues
bash
# Use virtual environments instead of system Python
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install bitchute-scraper
4. Missing Dependencies
bash
# Install with all dependencies
pip install bitchute-scraper[full]

# Or check specific error and install missing package
pip install <missing-package>
Platform-Specific Notes
Windows
Use pip install bitchute-scraper[full] for best compatibility
Chrome installation may require manual download
Use Command Prompt or PowerShell, not Git Bash for pip commands
macOS
Xcode command line tools may be required: xcode-select --install
For Apple Silicon, prefer conda for numpy/pandas if issues arise
Chrome is usually automatically detected
Linux
Install Chrome/Chromium: sudo apt-get install chromium-browser
May need build tools: sudo apt-get install build-essential python3-dev
Virtual display for headless: sudo apt-get install xvfb
Publishing (Maintainers Only)
1. Prepare Release
bash
# Update version in bitchute/__init__.py
# Update CHANGELOG.md
# Create git tag
git tag v1.1.0
git push origin v1.1.0
2. Build and Upload
bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build distributions
python -m build

# Check distributions
twine check dist/*

# Upload to Test PyPI first
twine upload --repository testpypi dist/*

# Test installation from Test PyPI
pip install --index-url https://test.pypi.org/simple/ bitchute-scraper

# Upload to PyPI
twine upload dist/*
3. Post-Release
bash
# Update version to next development version
# Update documentation
# Create GitHub release with changelog
Environment Variables
Optional Configuration
bash
# Set custom Chrome binary path (if needed)
export CHROME_BINARY_PATH="/path/to/chrome"

# Set custom download directory
export BITCHUTE_DOWNLOAD_DIR="/path/to/downloads"

# Enable debug logging
export BITCHUTE_DEBUG=1

# Set custom cache directory
export BITCHUTE_CACHE_DIR="/path/to/cache"
Docker Usage (Optional)
Dockerfile Example
dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    chromium-browser \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV CHROME_BINARY_PATH=/usr/bin/chromium-browser
ENV PYTHONUNBUFFERED=1

# Install package
RUN pip install bitchute-scraper[full]

# Set working directory
WORKDIR /app

# Default command
CMD ["bitchute-scraper", "--help"]
Build and Run
bash
# Build image
docker build -t bitchute-scraper .

# Run container
docker run -v $(pwd)/data:/app/data bitchute-scraper trending --limit 10
Performance Optimization
Large-Scale Usage
bash
# Install with fast data formats
pip install bitchute-scraper[fast,monitoring]

# Use multiple workers
api = BitChuteAPI(max_workers=10, rate_limit=0.1)

# Enable monitoring
api = BitChuteAPI(verbose=True)
Memory Optimization
bash
# Process data in chunks for large datasets
for chunk in pd.read_csv('large_file.csv', chunksize=1000):
    process_chunk(chunk)
Getting Help
📚 Documentation: README.md
🐛 Issues: GitHub Issues
💬 Discussions: GitHub Discussions
📧 Email: marcus.burkhardt@gmail.com
License
This project is licensed under the MIT License - see the LICENSE file for details.