#!/usr/bin/env python3
"""
BitChute Scraper Setup Configuration
"""

from setuptools import setup, find_packages
from pathlib import Path
import re

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read version from __init__.py
def get_version():
    init_file = this_directory / "bitchute" / "__init__.py"
    if init_file.exists():
        content = init_file.read_text(encoding='utf-8')
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    return "1.1.0"

# Read package info from __init__.py
def get_package_info():
    init_file = this_directory / "bitchute" / "__init__.py"
    info = {
        'version': '1.0.0',
        'author': 'Marcus Burkhardt',
        'email': 'marcus.burkhardt@gmail.com',
        'description': 'API-based package to scrape BitChute platform data with automatic download capabilities.',
        'url': 'https://github.com/bumatic/bitchute-scraper'
    }
    
    if init_file.exists():
        content = init_file.read_text(encoding='utf-8')
        
        patterns = {
            'version': r'__version__\s*=\s*["\']([^"\']+)["\']',
            'author': r'__author__\s*=\s*["\']([^"\']+)["\']',
            'email': r'__email__\s*=\s*["\']([^"\']+)["\']',
            'description': r'__description__\s*=\s*["\']([^"\']+)["\']',
            'url': r'__url__\s*=\s*["\']([^"\']+)["\']'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                info[key] = match.group(1)
    
    return info

# Get package information
pkg_info = get_package_info()

# Core requirements - minimal dependencies needed for basic functionality
CORE_REQUIREMENTS = [
    "requests>=2.28.0",
    "pandas>=1.5.0",
    "python-dateutil>=2.8.0",
    "retrying>=1.3.0",
]

# Selenium requirements for token extraction
SELENIUM_REQUIREMENTS = [
    "selenium>=4.10.0",
    "webdriver-manager>=3.8.0",
]

# Download requirements
DOWNLOAD_REQUIREMENTS = [
    "urllib3>=1.26.0",
]

# Export format requirements
EXPORT_REQUIREMENTS = [
    "openpyxl>=3.0.0",  # Excel export
]

# Optional requirements that enhance functionality but aren't strictly needed
OPTIONAL_REQUIREMENTS = [
    "tqdm>=4.64.0",      # Progress bars for downloads
    "pyarrow>=10.0.0",   # Parquet export (fast columnar format)
    "psutil>=5.8.0",     # System monitoring
    "pyyaml>=6.0",       # YAML configuration support
]

# Development requirements
DEV_REQUIREMENTS = [
    "pytest>=7.0.0",
    "pytest-mock>=3.10.0",
    "pytest-cov>=4.0.0",
    "black>=22.0.0",
    "flake8>=5.0.0",
    "mypy>=1.0.0",
    "types-requests>=2.28.0",
    "types-python-dateutil>=2.8.0",
]

# Documentation requirements
DOCS_REQUIREMENTS = [
    "sphinx>=5.0.0",
    "sphinx-rtd-theme>=1.0.0",
    "myst-parser>=0.18.0",  # For Markdown support in Sphinx
]

# Combined requirements for different installation scenarios
ALL_REQUIREMENTS = (
    CORE_REQUIREMENTS + 
    SELENIUM_REQUIREMENTS + 
    DOWNLOAD_REQUIREMENTS + 
    EXPORT_REQUIREMENTS + 
    OPTIONAL_REQUIREMENTS
)

setup(
    # Basic package information
    name="bitchute-scraper",
    version=pkg_info['version'],
    description=pkg_info['description'],
    long_description=long_description,
    long_description_content_type="text/markdown",
    
    # Author information
    author=pkg_info['author'],
    author_email=pkg_info['email'],
    maintainer=pkg_info['author'],
    maintainer_email=pkg_info['email'],
    
    # URLs
    url=pkg_info['url'],
    project_urls={
        "Bug Reports": f"{pkg_info['url']}/issues",
        "Source": pkg_info['url'],
        "Documentation": f"{pkg_info['url']}/blob/main/README.md",
        "Changelog": f"{pkg_info['url']}/blob/main/CHANGELOG.md",
    },
    
    # Package configuration
    packages=find_packages(),
    package_dir={"": "."},
    
    # Include non-Python files
    include_package_data=True,
    package_data={
        "bitchute": ["*.txt", "*.md", "*.json"],
    },
    
    # Requirements
    python_requires=">=3.7",
    install_requires=CORE_REQUIREMENTS + SELENIUM_REQUIREMENTS + DOWNLOAD_REQUIREMENTS + EXPORT_REQUIREMENTS,
    
    # Optional dependencies that can be installed with extras
    extras_require={
        # Full installation with all features
        "full": ALL_REQUIREMENTS,
        
        # Optional enhancements
        "optional": OPTIONAL_REQUIREMENTS,
        
        # Progress bars and enhanced UX
        "progress": ["tqdm>=4.64.0"],
        
        # Fast data formats
        "fast": ["pyarrow>=10.0.0"],
        
        # System monitoring
        "monitoring": ["psutil>=5.8.0"],
        
        # Configuration management
        "config": ["pyyaml>=6.0"],
        
        # Development tools
        "dev": DEV_REQUIREMENTS,
        
        # Documentation tools
        "docs": DOCS_REQUIREMENTS,
        
        # Testing only
        "test": [
            "pytest>=7.0.0",
            "pytest-mock>=3.10.0",
            "pytest-cov>=4.0.0",
        ],
        
        # Code quality tools
        "lint": [
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "types-requests>=2.28.0",
            "types-python-dateutil>=2.8.0",
        ],
    },
    
    # Entry points for command-line interface
    entry_points={
        "console_scripts": [
            "bitchute-scraper=bitchute.cli:main",
            "bitchute=bitchute.cli:main",
        ],
    },
    
    # Classification
    classifiers=[
        # Development Status
        "Development Status :: 5 - Production/Stable",
        
        # Intended Audience
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Information Technology",
        
        # License
        "License :: OSI Approved :: MIT License",
        
        # Programming Language
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        
        # Operating System
        "Operating System :: OS Independent",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        
        # Topic
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Multimedia :: Video",
        "Topic :: Internet :: File Transfer Protocol (FTP)",
        "Topic :: Database",
        "Topic :: Text Processing :: General",
        
        # Framework
        "Framework :: Jupyter",
        
        # Environment
        "Environment :: Console",
        "Environment :: Web Environment",
    ],
    
    # Keywords for PyPI search
    keywords=[
        "bitchute", "api", "scraper", "video", "data-collection", 
        "download", "media", "research", "social-media", "content-analysis",
        "web-scraping", "data-science", "automation", "bulk-download",
        "platform-data", "video-metadata", "channel-analytics"
    ],
    
    # Minimum Python version and compatibility
    zip_safe=False,  # Package contains non-Python files
    
    # License
    license="MIT",
    
    # Platform compatibility
    platforms=["any"],
    
    # Additional metadata for PyPI
    download_url=f"{pkg_info['url']}/archive/v{pkg_info['version']}.tar.gz",
)