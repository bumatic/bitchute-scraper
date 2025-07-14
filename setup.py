"""
Setup configuration for BitChute Scraper
"""

import setuptools
from pathlib import Path

# Read README file
readme_file = Path(__file__).parent / "README.md"
if readme_file.exists():
    with open(readme_file, "r", encoding="utf-8") as fh:
        long_description = fh.read()
else:
    long_description = "A package to extract BitChute platform recommendations using official API endpoints"

# Core dependencies
install_requires = [
    'requests>=2.28.0',
    'pandas>=1.5.0',
    'selenium>=4.10.0',
    'webdriver-manager>=3.8.0',
    'retrying>=1.3.0',
    'python-dateutil>=2.8.0',
]

# Optional dependencies
extras_require = {
    'full': [
        'openpyxl>=3.0.0',      # Excel export
        'pyarrow>=10.0.0',      # Parquet export
        'psutil>=5.8.0',        # Performance monitoring
        'pyyaml>=6.0',          # Configuration files
    ],
    'dev': [
        'pytest>=7.0.0',
        'pytest-mock>=3.10.0',
        'pytest-cov>=4.0.0',
        'black>=22.0.0',
        'flake8>=5.0.0',
        'mypy>=1.0.0',
    ],
    'docs': [
        'sphinx>=5.0.0',
        'sphinx-rtd-theme>=1.0.0',
    ]
}

# Add 'all' extra that includes everything
extras_require['all'] = list(set(
    dep for deps in extras_require.values() for dep in deps
))

setuptools.setup(
    name="bitchute-scraper",
    version="2.0.0",
    author="Marcus Burkhardt",
    author_email="marcus.burkhardt@gmail.com",
    description="A package to extract BitChute platform recommendations using official API endpoints",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bumatic/bitchute-scraper",
    project_urls={
        "Bug Tracker": "https://github.com/bumatic/bitchute-scraper/issues",
        "Documentation": "https://github.com/bumatic/bitchute-scraper#readme",
        "Source Code": "https://github.com/bumatic/bitchute-scraper",
    },
    packages=setuptools.find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Typing :: Typed",
    ],
    python_requires='>=3.7',
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points={
        'console_scripts': [
            'bitchute-scraper=bitchute.cli:main',
            'bitchute=bitchute.cli:main',  # Shorter alias
        ],
    },
    keywords=[
        'bitchute', 'api', 'scraper', 'video', 'data-collection',
        'social-media', 'research', 'analytics', 'content-analysis'
    ],
    package_data={
        'bitchute': [
            'py.typed',  # Indicate that this package supports type hints
        ],
    },
    include_package_data=True,
    zip_safe=False,  # Required for proper package discovery
)


